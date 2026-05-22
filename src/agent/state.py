from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class TravelIntent(TypedDict):
    destination: str        # 목적지 (예: "부산")
    check_in: str           # 체크인 날짜 YYYY-MM-DD
    check_out: str          # 체크아웃 날짜 YYYY-MM-DD
    budget: int             # 총 예산 (원)
    adults: int             # 인원


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

    # 1. Intent Router 출력
    intent: TravelIntent | None

    # 2. Weather Node 출력
    is_rainy: bool
    weather_summary: str    # 날씨 한 줄 요약 (synthesizer에 전달)

    # 3. Stay Node 출력
    hotel_name: str
    hotel_address: str
    hotel_cost: int         # 숙박비 (원)
    remaining_budget: int   # 잔여 예산

    # 4. Place Node 출력
    restaurants: list       # [{"title": ..., "address": ..., "category": ...}]
    attractions: list       # [{"title": ..., "address": ..., "category": ...}]

    # 5. Synthesizer 출력
    final_report: str       # 최종 마크다운 리포트
