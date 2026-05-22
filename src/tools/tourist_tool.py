from typing import List, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool

# 원래 기능이 있는 tourist 폴더에서 직접 가져옵니다.
from tourist.google_places import search_places
from tourist.naver_local import search_local

class IntlPlaceArgs(BaseModel):
    query: str = Field(..., description="해외 장소 검색어 (예: '도쿄 시부야 스시', '오사카 카페')")

@tool(args_schema=IntlPlaceArgs)
def tool_search_intl_places(query: str) -> List[Dict[str, Any]]:
    """(해외 전용) 한국을 제외한 전 세계의 식당, 명소 등을 검색합니다."""
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
    """(국내 전용) 한국 내의 식당, 카페, 명소를 검색합니다."""
    try:
        places = search_local(query=query, display=5)
        return [{
            "name": getattr(p, "name", "이름 없음"),
            "address": getattr(p, "address", "주소 없음"),
            "category": getattr(p, "category", "분류 없음")
        } for p in places]
    except Exception as e:
        return [{"error": str(e)}]