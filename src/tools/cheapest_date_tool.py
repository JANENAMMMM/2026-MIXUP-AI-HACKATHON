from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from cheapest_date.flight_crawler import get_cheapest_dates


# ==========================================
# 날짜 미정 최저가 항공권 검색 Tool (Naver Flights)
# ==========================================
# 네이버 항공권 GraphQL API를 통해 특정 월(들)과 여행 일수를 기준으로
# 가장 저렴한 출발 날짜 조합을 상위 5개 반환한다.
#
# 사용 시나리오:
#   - 사용자가 "6~7월 중 제일 싼 날짜로 도쿄 4박5일 가고 싶어" 처럼
#     날짜가 아직 정해지지 않은 경우에 이 tool을 사용한다.
#   - 날짜가 확정된 경우에는 transport_tools.tool_search_flights를 사용한다.
# ==========================================

class CheapestDateArgs(BaseModel):
    origin: str = Field(..., description="출발 공항 IATA 코드 (예: 'ICN')")
    destination: str = Field(..., description="도착 공항 IATA 코드 (예: 'NRT', 'LHR', 'CDG')")
    months: List[str] = Field(..., description="조회할 연월 목록. YYYYMM 형식 문자열 배열 (예: ['202606', '202607'])")
    trip_days: List[int] = Field(..., description="여행 총 일수 배열. 박(泊)이 아닌 일(日) 기준 (예: 3박4일 → [4])")
    is_nonstop: bool = Field(default=False, description="True이면 직항 항공편만 조회. 기본값 False(경유 포함)")


@tool(args_schema=CheapestDateArgs)
def tool_get_cheapest_flight_dates(
    origin: str,
    destination: str,
    months: List[str],
    trip_days: List[int],
    is_nonstop: bool = False,
) -> List[Dict[str, Any]]:
    """
    날짜가 정해지지 않은 상태에서 가장 저렴한 항공권 날짜 조합을 찾아줍니다.

    사용 조건:
    - 사용자가 "언제가 제일 싸?", "저렴한 날짜로 가고 싶어", "여름방학/추석 연휴에 가고 싶어" 처럼
      출발일이 미확정인 경우에 이 도구를 사용합니다.
    - 사용자가 특정 날짜를 이미 말한 경우에는 이 도구 대신
      tool_search_flights를 사용하세요.
    - 최적 날짜를 추천할 때는 이 도구의 결과와 tool_get_weather의 날씨 정보를
      함께 참고하여 가격과 날씨를 종합적으로 판단하세요.

    반환값 (최대 5개, 가격 오름차순):
    - departure_date: 출발 날짜 (YYYY-MM-DD)
    - return_date: 귀국 날짜 (YYYY-MM-DD)
    - price_krw: 왕복 최저가 (원화)
    - trip_days: 총 여행 일수 (박+1)
    - airlines: 운항 항공사 코드 목록
    - stops: 경유 횟수 (0=직항)

    주의:
    - months는 반드시 'YYYYMM' 형식 (예: '202607')으로 전달해야 합니다.
    - trip_days는 '박' 수가 아닌 '일' 수입니다 (3박4일 → 4).
    - 결과가 없으면 조회 월 범위를 넓히거나 trip_days 범위를 조정해 보세요.
    """
    try:
        results = get_cheapest_dates(
            origin=origin,
            destination=destination,
            months=months,
            trip_days=trip_days,
            is_nonstop=is_nonstop,
            top_n=5,
        )

        if not results:
            return [{"message": "조건에 맞는 최저가 항공권 정보를 찾을 수 없습니다. months 범위를 넓히거나 trip_days를 조정해 보세요."}]

        return [
            {
                "departure_date": f.date,
                "return_date": f.return_date,
                "price_krw": f.price,
                "trip_days": f.trip_days,
                "airlines": f.airline_codes,
                "stops": f.stops,
            }
            for f in results
        ]

    except Exception as e:
        return [{"error": f"최저가 날짜 조회 중 오류 발생: {str(e)}"}]
