from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage
from src.agent import build_graph

app = build_graph()


def main() -> None:
    print("여행 AI 에이전트입니다. 종료하려면 'exit'을 입력하세요.\n")
    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() == "exit":
            break
        result = app.invoke({
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
            "restaurants": [],
            "attractions": [],
            "final_report": "",
        })
        print(f"\n{result.get('final_report') or result['messages'][-1].content}\n")


if __name__ == "__main__":
    main()
