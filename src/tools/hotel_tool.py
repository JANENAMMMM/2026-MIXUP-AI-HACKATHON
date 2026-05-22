import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool

# 같은 폴더(hotel) 내의 파일에서 가져옴
from hotel.search import search_google_hotels
from hotel.models import HotelSearchRequest

class HotelSearchArgs(BaseModel):
    query: str = Field(..., description="검색할 목적지 (예: '도쿄 시부야', '해운대')")
    check_in_date: str = Field(..., description="체크인 날짜 (YYYY-MM-DD)")
    check_out_date: str = Field(..., description="체크아웃 날짜 (YYYY-MM-DD)")
    adults: int = Field(default=2, description="성인 투숙객 수")
    max_price: Optional[int] = Field(default=None, description="1박당 최대 가격(KRW). 예산 제한이 있을 때 사용")

@tool(args_schema=HotelSearchArgs)
def tool_search_hotels(query: str, check_in_date: str, check_out_date: str, adults: int = 2, max_price: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    사용자가 여행 일정 중 머물 호텔, 리조트 등 숙소를 찾아달라고 요청할 때 사용하는 검색 도구입니다.

    [ 필수 행동 지침 ]
    1. 예산 제약식 (Budget Balancing): 사용자가 전체 여행 예산을 제시했다면, 숙박에 쓸 수 있는 최대 예산은 '총 예산의 60%'로 제한됩니다. LLM은 총 예산의 60%를 숙박 일수로 나눈 '1박당 최대 금액'을 스스로 계산하여 `max_price` 파라미터에 반드시 입력해야 합니다.
    2. 선호 숙소 우회 (Bypass): 사용자가 "신라호텔로 찾아줘"처럼 특정 숙소 이름을 명확히 지정한 경우에는, 예산 60% 제약을 무시하고 해당 숙소를 바로 검색하세요.
    3. 선행 조건: 이 도구를 사용하려면 여행 날짜(check_in_date, check_out_date)가 반드시 확정되어 있어야 합니다. 날짜가 미정이라면 Date Optimizer 관련 도구를 먼저 사용하세요.
    """
    api_key = os.getenv("SERPAPI_KEY")
    try:
        request = HotelSearchRequest(
            q=query, check_in_date=check_in_date, check_out_date=check_out_date,
            adults=adults, max_price=max_price, currency="KRW", hl="ko", gl="kr"
        )
        result = search_google_hotels(api_key=api_key, request=request)
        
        return [{
            "name": h.name, 
            "price_per_night": h.rate_per_night, 
            "total_price": h.total_rate,
            "rating": h.overall_rating,
            "amenities": h.amenities[:5]
        } for h in result.hotels[:3]]
    except Exception as e:
        return [{"error": str(e)}]