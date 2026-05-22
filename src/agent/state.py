from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class TravelIntent(TypedDict):
    destination: str        # 목적지 (예: "런던")
    check_in: str           # 체크인 날짜 YYYY-MM-DD (date_fixed=False면 빈 문자열)
    check_out: str          # 체크아웃 날짜 YYYY-MM-DD
    budget: int             # 총 예산 (원)
    adults: int             # 인원
    trip_nights: int        # 숙박 일수
    target_months: list     # 검색 대상 월 목록 (예: ["202607"]) — date_fixed=False일 때 사용
    prefer_nonstop: bool    # True면 직항 선호 → 경유 감점 폭 증가
    preferred_hotel: str | None  # 사용자가 명시한 선호 호텔명 (없으면 null)
    flight_cost: int        # 선택된 항공권 가격 (왕복, 옵션)


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

    # 1. Intent Router 출력
    intent: TravelIntent | None
    date_fixed: bool            # False = 날짜 미정 → date_optimizer 실행

    # 2. Date Optimizer 출력 (날짜 미정일 때만)
    candidate_dates: list       # TOP 3: [{"check_in", "check_out", "flight_price", "weather_summary", "score", "reason"}]

    # 3. Weather Node 출력
    is_rainy: bool
    weather_summary: str

    # 4. Stay Node 출력
    hotel_name: str
    hotel_address: str
    hotel_cost: int
    remaining_budget: int
    hotel_candidates: list  # 예산 내 추천 후보 3곳 (선호 호텔 없을 때 채워짐)

    # 5. Place Node 출력
    restaurants: list
    attractions: list
    route_note: str  # 위치 기반 최적 동선 요약 (좌표 없으면 빈 문자열)

    # 6. Synthesizer 출력
    final_report: str
