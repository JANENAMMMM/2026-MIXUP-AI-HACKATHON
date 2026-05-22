import os
import uuid

from dotenv import load_dotenv
load_dotenv()

from langchain_core.messages import HumanMessage
from langchain_core.tracers.langchain import LangChainTracer
from langchain_core.tracers.langchain import wait_for_all_tracers
from langgraph.types import Command
from src.agent import build_graph

app = build_graph()


def _show_hotel_candidates(interrupt_val: dict) -> str:
    """호텔 후보 목록을 출력하고 사용자 선택(1/2/3)을 받는다."""
    candidates = interrupt_val.get("candidates", [])
    print(f"\n{interrupt_val.get('question', '숙소를 선택해주세요:')}")

    for i, h in enumerate(candidates, 1):
        cost_str = f"{h['cost']:,}원" if h.get("cost", 0) > 0 else "가격 미확인"
        rating_str = f" ★{h['rating']}" if h.get("rating") else ""
        print(f"  {i}) {h['name']} | {cost_str}{rating_str}")
        if h.get("address"):
            print(f"      위치        : {h['address']}")
        if h.get("description"):
            print(f"      주요 특징   : {h['description']}")
        if h.get("amenities"):
            print(f"      편의시설     : {', '.join(h['amenities'])}")
        # 상세 링크와 썸네일은 값이 있을 때만 출력
        details_link = h.get("details_link")
        if details_link:
            print(f"      상세 링크   : {details_link}")
        image_url = h.get("image_url")
        if image_url:
            print(f"      이미지 URL : {image_url}")

    while True:
        choice = input(f"\n번호를 선택하세요 (1~{len(candidates)}): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(candidates):
            return choice
        print(f"  1~{len(candidates)} 사이의 숫자를 입력해주세요.")


def _initial_state(user_input: str) -> dict:
    return {
        "messages": [HumanMessage(content=user_input)],
        "intent": None,
        "date_fixed": True,
        "candidate_dates": [],
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


def main() -> None:
    print("여행 AI 에이전트입니다. 종료하려면 'exit'을 입력하세요.\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "exit":
            break

        # 대화마다 새 thread_id로 격리, LangSmith 트레이서 명시 주입
        tracer = LangChainTracer(
            project_name=os.getenv("LANGSMITH_PROJECT", "default")
        )
        config = {
            "configurable": {"thread_id": str(uuid.uuid4())},
            "callbacks": [tracer],
        }

        result = app.invoke(_initial_state(user_input), config=config)

        # interrupt 감지 루프 (stay_node의 호텔 선택 등)
        snapshot = app.get_state(config)
        while snapshot.next:
            interrupts = snapshot.tasks[0].interrupts if snapshot.tasks else []
            if not interrupts:
                break
            val = interrupts[0].value
            if isinstance(val, dict) and val.get("type") == "hotel_selection":
                choice = _show_hotel_candidates(val)
                result = app.invoke(Command(resume=choice), config=config)
                snapshot = app.get_state(config)
            else:
                break

        # 트레이스가 백그라운드 스레드에서 전송 완료될 때까지 대기
        wait_for_all_tracers()

        print(f"\n{result.get('final_report') or result['messages'][-1].content}\n")


if __name__ == "__main__":
    main()
