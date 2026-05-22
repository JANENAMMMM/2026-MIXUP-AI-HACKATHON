import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from api.schemas import PlanRequest, PlanResponse
from src.agent import build_graph

router = APIRouter()

_app = None


def _get_app():
    global _app
    if _app is None:
        _app = build_graph(interactive=False)
    return _app


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


@router.post("/plan", response_model=PlanResponse)
async def create_plan(req: PlanRequest) -> PlanResponse:
    """사용자 메시지를 받아 LangGraph 파이프라인을 실행하고 여행 계획을 반환한다."""
    app = _get_app()
    user_msg = _build_user_message(req)

    result = await asyncio.to_thread(
        app.invoke,
        {
            "messages": [HumanMessage(content=user_msg)],
            "intent": None,
            "is_rainy": False,
            "weather_summary": "",
            "hotel_name": "",
            "hotel_address": "",
            "hotel_cost": 0,
            "remaining_budget": 0,
            "hotel_candidates": [],
            "restaurants": [],
            "attractions": [],
            "final_report": "",
        },
    )

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
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(
            None,
            lambda: app.invoke(
                {
                    "messages": [HumanMessage(content=user_msg)],
                    "intent": None,
                    "is_rainy": False,
                    "weather_summary": "",
                    "hotel_name": "",
                    "hotel_address": "",
                    "hotel_cost": 0,
                    "remaining_budget": 0,
                    "hotel_candidates": [],
                    "restaurants": [],
                    "attractions": [],
                    "final_report": "",
                }
            ),
        )

        # 그래프가 완료되기 전까지 진행 중 이벤트를 전송한다
        # TODO: LangGraph stream_mode="updates"를 사용하면 노드별 실시간 이벤트 가능
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
