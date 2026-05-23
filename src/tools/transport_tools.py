from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from transport.flights import search_flights
from transport.transit import search_transit
from cheapest_date.flight_crawler import get_cheapest_dates

# ==========================================
# 1. 특정 날짜 항공권 검색 Tool (Google Flights)
# ==========================================
class FlightSearchArgs(BaseModel):
    departure_id: str = Field(..., description="출발 공항 IATA 코드 (예: ICN)")
    arrival_id: str = Field(..., description="도착 공항 IATA 코드 (예: NRT)")
    outbound_date: str = Field(..., description="출발 날짜 (YYYY-MM-DD 형식)")
    return_date: Optional[str] = Field(default=None, description="돌아오는 날짜 (왕복인 경우에만 YYYY-MM-DD 형식으로 입력)")

@tool(args_schema=FlightSearchArgs)
def tool_search_flights(departure_id: str, arrival_id: str, outbound_date: str, return_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """확정된 날짜의 항공편을 검색해 항공사·시간·가격·경유 정보를 반환한다."""
    try:
        result = search_flights(
            departure_id=departure_id, 
            arrival_id=arrival_id, 
            outbound_date=outbound_date, 
            return_date=return_date, 
            max_results=3
        )
        if getattr(result, "error", None):
            return [{"error": result.error}]
            
        return [{
            "airline": getattr(f, "airline", "알 수 없음"),
            "flight_number": getattr(f, "flight_number", ""),
            "departure_time": getattr(f, "departure_time", ""),
            "arrival_time": getattr(f, "arrival_time", ""),
            "price": getattr(f, "total_price", 0),
            "stops": getattr(f, "stops", 0)
        } for f in result.flights]
    except Exception as e:
        return [{"error": f"항공편 검색 중 오류 발생: {str(e)}"}]


# ==========================================
# 2. 대중교통 경로 검색 Tool (Google Transit)
# ==========================================
class TransitSearchArgs(BaseModel):
    start_addr: str = Field(..., description="출발지 주소 또는 장소명 (예: '해운대 신라스테이', '도쿄 타워')")
    end_addr: str = Field(..., description="도착지 주소 또는 장소명 (예: '광안리 해수욕장', '시부야 스크램블 교차로')")

@tool(args_schema=TransitSearchArgs)
def tool_search_transit(start_addr: str, end_addr: str) -> Dict[str, Any]:
    """두 장소 사이의 대중교통 최적 경로와 예상 이동 시간(분)을 반환한다."""
    try:
        result = search_transit(start_addr=start_addr, end_addr=end_addr, max_results=1)
        if getattr(result, "error", None):
            return {"error": result.error}
            
        route = result.routes[0]
        return {
            "start": result.start,
            "end": result.end,
            "duration_minutes": getattr(route, "duration", "정보 없음")
        }
    except Exception as e:
        return {"error": f"대중교통 검색 중 오류 발생: {str(e)}"}