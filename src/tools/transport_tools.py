from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool

# ==========================================
# [Import] 원본 비즈니스 로직 함수 가져오기
# ==========================================
from transport.flights import search_flights
from transport.transit import search_transit

# ⚠️ 새로 만드신 네이버 항공권 크롤러 파일 이름에 맞게 아래 임포트 문을 수정해주세요. 
# (예: 파일명이 naver_flight.py 인 경우)
from transport.naver_flight import get_cheapest_dates


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
    사용자가 '특정 날짜'를 지정하여 출발지와 도착지 간의 최적 항공편을 검색할 때 사용합니다.
    (날짜가 아직 정해지지 않았다면 이 도구 대신 tool_get_cheapest_flight_dates를 사용하세요.)
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
# 2. 날짜 미정 최저가 항공권 검색 Tool (Naver Flights)
# ==========================================
class CheapestFlightDatesArgs(BaseModel):
    origin: str = Field(..., description="출발 공항 IATA 코드 (예: 'ICN')")
    destination: str = Field(..., description="도착 공항 IATA 코드 (예: 'NRT', 'LHR')")
    months: List[str] = Field(..., description="조회할 연월 목록 (반드시 YYYYMM 형식의 문자열 배열이어야 함. 예: ['202606', '202607'])")
    trip_days: List[int] = Field(..., description="원하는 여행 일수 배열 (예: 3박 4일 일정이라면 [4] 입력)")
    is_nonstop: bool = Field(default=False, description="직항만 검색할지 여부 (기본값: False)")

@tool(args_schema=CheapestFlightDatesArgs)
def tool_get_cheapest_flight_dates(
    origin: str, 
    destination: str, 
    months: List[str], 
    trip_days: List[int], 
    is_nonstop: bool = False
) -> List[Dict[str, Any]]:
    """
    사용자가 '날짜 미정' 상태로 가장 저렴한 여행 날짜를 추천해달라고 할 때 사용하는 도구입니다.
    특정 달(month)과 여행 일수(trip_days)를 기반으로 날짜별 최저가 항공권 상위 5개를 반환합니다.
    """
    try:
        # LLM이 너무 많은 데이터를 받아 컨텍스트가 터지지 않게 상위 5개만 가져옵니다.
        results = get_cheapest_dates(
            origin=origin,
            destination=destination,
            months=months,
            trip_days=trip_days,
            is_nonstop=is_nonstop,
            top_n=5 
        )
        
        if not results:
            return [{"message": "조건에 맞는 항공권 최저가 정보를 찾을 수 없습니다."}]
            
        # LLM이 읽기 편하게 객체(FlightPrice)를 JSON(dict) 리스트로 변환
        return [{
            "departure_date": f.date,
            "return_date": getattr(f, "return_date", "정보 없음"),
            "price_krw": f.price,
            "trip_days": f.trip_days,
            "airlines": f.airline_codes,
            "stops": f.stops
        } for f in results]

    except Exception as e:
        return [{"error": f"최저가 날짜 검색 중 오류 발생: {str(e)}"}]


# ==========================================
# 3. 대중교통 경로 검색 Tool (Google Transit)
# ==========================================
class TransitSearchArgs(BaseModel):
    start_addr: str = Field(..., description="출발지 주소 또는 지명")
    end_addr: str = Field(..., description="도착지 주소 또는 지명")

@tool(args_schema=TransitSearchArgs)
def tool_search_transit(start_addr: str, end_addr: str) -> Dict[str, Any]:
    """두 장소 사이의 대중교통 경로와 예상 소요 시간(분)을 검색합니다."""
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