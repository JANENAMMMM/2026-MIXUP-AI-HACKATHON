import asyncio
import json
import threading
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from langgraph.types import Command

from api.schemas import PlanRequest, PlanResponse, ResumeRequest, RefineRequest, StartPlanResponse
from src.agent import build_graph
from src.agent.progress import register as progress_register, set_run_id, unregister as progress_unregister

router = APIRouter()

_app = None


def _get_app():
    global _app
    if _app is None:
        _app = build_graph()
    return _app


def _initial_state(user_msg: str) -> dict:
    return {
        "messages": [HumanMessage(content=user_msg)],
        "intent": None,
        "date_fixed": True,
        "candidate_dates": [],
        "is_rainy": False,
        "weather_summary": "",
        "hotel_prefs": {},
        "hotel_name": "",
        "hotel_address": "",
        "hotel_cost": 0,
        "remaining_budget": 0,
        "hotel_candidates": [],
        "restaurants": [],
        "attractions": [],
        "route_note": "",
        "final_report": "",
        "refinement_feedback": "",
    }


def _build_plan_response(result: dict) -> PlanResponse:
    return PlanResponse(
        intent=result.get("intent") or {},
        weather_summary=result.get("weather_summary", ""),
        hotel_name=result.get("hotel_name", ""),
        hotel_address=result.get("hotel_address", ""),
        hotel_cost=result.get("hotel_cost", 0),
        remaining_budget=result.get("remaining_budget", 0),
        restaurants=result.get("restaurants", []),
        attractions=result.get("attractions", []),
        final_report=result.get("final_report", ""),
    )


def _check_interrupt(app, config: dict) -> dict | None:
    """interrupt 발생 여부를 확인하고 값을 반환한다. 없으면 None."""
    snapshot = app.get_state(config)
    if not snapshot.next:
        return None
    interrupts = snapshot.tasks[0].interrupts if snapshot.tasks else []
    if not interrupts:
        return None
    return interrupts[0].value if isinstance(interrupts[0].value, dict) else None


def _build_user_message(req: PlanRequest) -> str:
    """사용자 입력과 명확화 답변을 하나의 메시지로 합친다."""
    parts = [req.message]
    if req.budget:
        parts.append(f"예산: {req.budget}")
    if req.people:
        parts.append(f"인원: {req.people}")
    if req.stay:
        parts.append(f"숙소 선호: {req.stay}")
    return " / ".join(parts)


@router.post("/plan/start", response_model=StartPlanResponse)
async def start_plan(req: PlanRequest) -> StartPlanResponse:
    """그래프를 시작하고 첫 번째 interrupt(날짜/호텔 선택) 또는 완료 결과를 반환한다."""
    app = _get_app()
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    user_msg = _build_user_message(req)

    result = await asyncio.to_thread(app.invoke, _initial_state(user_msg), config)

    interrupt_val = _check_interrupt(app, config)
    if interrupt_val:
        interrupt_type = interrupt_val.get("type", "")
        if interrupt_type in ("date_selection", "hotel_selection", "hotel_prefs"):
            if interrupt_type == "hotel_prefs":
                return StartPlanResponse(
                    thread_id=thread_id,
                    phase="hotel_prefs",
                    question=interrupt_val.get("question", ""),
                    schema=interrupt_val.get("schema", []),
                )
            return StartPlanResponse(
                thread_id=thread_id,
                phase=interrupt_type,
                question=interrupt_val.get("question", ""),
                candidates=interrupt_val.get("candidates", []),
            )

    return StartPlanResponse(
        thread_id=thread_id,
        phase="done",
        result=_build_plan_response(result),
    )


@router.post("/plan/resume", response_model=StartPlanResponse)
async def resume_plan(req: ResumeRequest) -> StartPlanResponse:
    """interrupt에서 재개한다. 또 다른 interrupt가 있으면 반환, 없으면 최종 결과 반환."""
    app = _get_app()
    config = {"configurable": {"thread_id": req.thread_id}}

    result = await asyncio.to_thread(
        app.invoke, Command(resume=req.choice), config
    )

    interrupt_val = _check_interrupt(app, config)
    if interrupt_val:
        interrupt_type = interrupt_val.get("type", "")
        if interrupt_type in ("date_selection", "hotel_selection"):
            return StartPlanResponse(
                thread_id=req.thread_id,
                phase=interrupt_type,
                question=interrupt_val.get("question", ""),
                candidates=interrupt_val.get("candidates", []),
            )
        if interrupt_type == "hotel_prefs":
            return StartPlanResponse(
                thread_id=req.thread_id,
                phase="hotel_prefs",
                question=interrupt_val.get("question", ""),
                schema=interrupt_val.get("schema", []),
            )

    return StartPlanResponse(
        thread_id=req.thread_id,
        phase="done",
        result=_build_plan_response(result),
    )


@router.post("/plan/refine", response_model=PlanResponse)
async def refine_plan(req: RefineRequest) -> PlanResponse:
    """기존 thread의 state를 읽어 synthesizer만 피드백과 함께 재실행한다."""
    from fastapi import HTTPException
    from src.agent.llm import get_llm
    from src.agent.nodes import make_synthesizer_node

    app = _get_app()
    config = {"configurable": {"thread_id": req.thread_id}}

    snapshot = app.get_state(config)
    if not snapshot or not snapshot.values:
        raise HTTPException(status_code=404, detail="Thread not found or expired")

    current_state = dict(snapshot.values)
    current_state["refinement_feedback"] = req.feedback

    llm = get_llm(model="solar-pro3", temperature=0.7)
    synth = make_synthesizer_node(llm)

    result = await asyncio.to_thread(synth, current_state)
    merged = {**current_state, **result}
    return _build_plan_response(merged)


@router.post("/plan/resume/stream")
async def resume_plan_stream(req: ResumeRequest) -> StreamingResponse:
    """hotel 선택 이후 나머지 노드(place, synth)를 실행하며 진행 상황을 SSE로 스트리밍한다."""

    async def event_gen() -> AsyncGenerator[str, None]:
        run_id = str(uuid.uuid4())
        progress_q = progress_register(run_id)
        app = _get_app()
        config = {"configurable": {"thread_id": req.thread_id}}
        result_box: dict = {}

        def _run() -> None:
            set_run_id(run_id)
            try:
                result_box["result"] = app.invoke(Command(resume=req.choice), config)
            except Exception as e:
                result_box["error"] = str(e)
            finally:
                progress_q.put_nowait({"type": "_done"})

        t = threading.Thread(target=_run, daemon=True)
        t.start()

        loop = asyncio.get_event_loop()
        while True:
            try:
                event = await loop.run_in_executor(None, lambda: progress_q.get(timeout=180))
            except Exception:
                break
            if event["type"] == "_done":
                break
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

        progress_unregister(run_id)

        if "error" in result_box:
            yield f"data: {json.dumps({'type': 'error', 'message': result_box['error']})}\n\n"
        elif "result" in result_box:
            interrupt_val = _check_interrupt(app, config)
            if interrupt_val:
                interrupt_type = interrupt_val.get("type", "")
                resp = StartPlanResponse(
                    thread_id=req.thread_id,
                    phase=interrupt_type,
                    question=interrupt_val.get("question", ""),
                    candidates=interrupt_val.get("candidates"),
                    schema=interrupt_val.get("schema"),
                )
            else:
                resp = StartPlanResponse(
                    thread_id=req.thread_id,
                    phase="done",
                    result=_build_plan_response(result_box["result"]),
                )
            yield f"data: {json.dumps({'type': 'final', **resp.model_dump()}, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/plan", response_model=PlanResponse)
async def create_plan(req: PlanRequest) -> PlanResponse:
    """사용자 메시지를 받아 LangGraph 파이프라인을 실행하고 여행 계획을 반환한다."""
    app = _get_app()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    user_msg = _build_user_message(req)

    result = await asyncio.to_thread(app.invoke, _initial_state(user_msg), config)
    return _build_plan_response(result)


@router.get("/plan/stream")
async def stream_plan(message: str, budget: str = "", people: str = "", stay: str = ""):
    """SSE 스트림으로 파이프라인 각 단계 완료 이벤트와 최종 결과를 전송한다."""
    req = PlanRequest(message=message, budget=budget or None, people=people or None, stay=stay or None)

    async def event_generator() -> AsyncGenerator[str, None]:
        # 각 파이프라인 단계 이름 → 프론트엔드 step id
        steps = ["orchestrator", "date", "stay", "budget", "place", "routing", "synth"]

        app = _get_app()
        user_msg = _build_user_message(req)

        # LangGraph 실행을 별도 스레드에서 돌린다
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(
            None,
            lambda: app.invoke(_initial_state(user_msg), config),
        )

        # 그래프가 완료되기 전까지 진행 중 이벤트를 전송한다
        for step in steps[:-1]:
            yield f"data: {json.dumps({'step': step, 'status': '진행중'})}\n\n"
            await asyncio.sleep(0.3)

        result = await future

        yield f"data: {json.dumps({'step': 'synth', 'status': '진행중'})}\n\n"

        payload = {
            "step": "synth",
            "status": "완료",
            "data": {
                "intent": result.get("intent") or {},
                "weather_summary": result.get("weather_summary", ""),
                "hotel_name": result.get("hotel_name", ""),
                "hotel_cost": result.get("hotel_cost", 0),
                "remaining_budget": result.get("remaining_budget", 0),
                "restaurants": result.get("restaurants", []),
                "attractions": result.get("attractions", []),
                "final_report": result.get("final_report", ""),
            },
        }
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
