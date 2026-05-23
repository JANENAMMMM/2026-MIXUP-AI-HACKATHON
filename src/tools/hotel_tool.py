import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool

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
    """Google Hotels API로 숙소를 검색해 이름/가격/평점/편의시설을 반환한다."""
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