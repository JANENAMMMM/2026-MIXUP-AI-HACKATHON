from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from cheapest_date.flight_crawler import get_cheapest_dates


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
    지정 월 내에서 왕복 최저가 날짜 조합을 최대 5개 반환한다.

    반환값: departure_date, return_date, price_krw, trip_days, airlines, stops
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
