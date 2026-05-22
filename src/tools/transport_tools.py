from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool

# ==========================================
# [Import] 원본 비즈니스 로직 함수 가져오기
# ==========================================
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
    """
    사용자가 여행 출발일과 도착일을 확실하게 '픽스(Fix)'한 경우, 출발지와 도착지 간의 최적 항공편을 검색하는 도구입니다.

    [ 필수 행동 지침 ]
    1. 날짜 미정 처리: 사용자가 "7월 중에", "제일 싼 날짜에" 처럼 날짜를 확정하지 않았다면, 절대 이 도구를 쓰지 말고 `tool_get_cheapest_flight_dates`를 사용하세요.
    2. 예산 연동 (Budget Balancing): 이 도구로 도출된 항공권 가격(price)은 유저의 '총 예산'에서 가장 먼저 차감되어야 합니다. 검색 결과를 바탕으로 잔여 예산을 계산하여 다음 에이전트(Stay, Place)가 사용할 수 있도록 상태(State)에 기록하세요.
    """
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
    """
    [ Routing Optimizer ] 두 장소 사이의 대중교통 최적 경로와 예상 이동 시간(분)을 계산하는 도구입니다.

    [ 필수 행동 지침 ]
    1. 사용 조건: Place & Dining Agent가 식당과 명소를 모두 찾아낸 후, 최종 일정표를 조립(Synthesizer)하기 위해 각 장소 간의 실제 이동 시간(duration_minutes)을 계산할 때 사용합니다.
    2. 동선 최적화 (TSP): '숙소 ↔ 명소', '명소 ↔ 식당' 간의 이동 시간을 각각 조회하여, 하루 일정 안에서 길에서 낭비하는 시간이 최소화되도록 동선 순서를 재배치하는 데 이 데이터(duration_minutes)를 활용하세요.
    3. 정확도: start_addr와 end_addr에는 이전 에이전트들이 검색해둔 장소의 정확한 '이름'이나 '주소'를 입력해야 정확한 이동 시간이 계산됩니다.
    """
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