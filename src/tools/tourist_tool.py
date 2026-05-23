from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool

from tourist.google_places import search_places
from tourist.naver_local import search_local

class IntlPlaceArgs(BaseModel):
    query: str = Field(..., description="해외 장소 검색어 (예: '도쿄 시부야 스시', '오사카 카페')")

@tool(args_schema=IntlPlaceArgs)
def tool_search_intl_places(query: str) -> List[Dict[str, Any]]:
    """Google Places API로 해외 식당·카페·관광 명소를 검색해 이름과 주소를 반환한다."""
    try:
        places = search_places(query=query)
        return [{
            "name": getattr(p, "name", "이름 없음"),
            "address": getattr(p, "address", "주소 없음")
        } for p in places[:5]]
    except Exception as e:
        return [{"error": str(e)}]

class DomesticPlaceArgs(BaseModel):
    query: str = Field(..., description="국내 장소 검색어 (예: '해운대 횟집', '제주도 가볼만한곳')")

@tool(args_schema=DomesticPlaceArgs)
def tool_search_domestic_places(query: str) -> List[Dict[str, Any]]:
    """네이버 지역 검색 API로 국내 식당·카페·관광 명소를 검색해 이름·주소·카테고리를 반환한다."""
    try:
        places = search_local(query=query, display=5)
        return [{
            "name": getattr(p, "name", "이름 없음"),
            "address": getattr(p, "address", "주소 없음"),
            "category": getattr(p, "category", "분류 없음")
        } for p in places]
    except Exception as e:
        return [{"error": str(e)}]