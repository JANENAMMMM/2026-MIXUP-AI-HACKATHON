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
    """
    (해외 전용) 한국을 제외한 전 세계의 식당, 카페, 관광 명소 등을 검색하는 도구입니다.

    [ 필수 행동 지침 ]
    1. 카테고리별 위치 전략 (Location Strategy):
       - 식당/카페 검색: 이전에 확정된 '숙소 위치' 또는 '방문 예정인 명소' 주변(Radius)을 중심으로 검색어를 작성하세요.
       - 관광 명소 검색: 숙소 위치에 얽매이지 말고, 해당 '도시/지역 전체'를 기준으로 가장 유명한 랜드마크와 필수 방문 코스를 검색하세요.
    2. 날씨 제약 (Weather Constraint): 날씨 에이전트가 확인한 해당 날짜의 날씨가 '비(Rain)' 등 악천후인 경우, 검색어에 "실내", "쇼핑몰", "박물관", "indoor" 등 비를 피할 수 있는 키워드를 반드시 포함하세요.
    3. 예산 제약 (Budget Balancing): 숙소 예약 후 남은 잔여 예산이 넉넉하지 않다면, 검색어에 "가성비", "저렴한", "cheap", "affordable" 등의 키워드를 강제로 추가하여 검색하세요.
    4. 사용 제한: 이 도구는 검색 지역이 해외일 때만 사용하세요.
    """
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
    """
    (국내 전용) 한국 내의 식당, 카페, 관광 명소 등을 검색하는 도구입니다.

    [ 필수 행동 지침 ]
    1. 카테고리별 위치 전략 (Location Strategy):
       - 식사/휴식: 피로도를 낮추기 위해 '숙소 근처' 또는 '현재 관광 중인 명소 근처'로 범위를 좁혀 검색어를 작성하세요.
       - 핫플/명소: 숙소 위치와 무관하게 '해당 도시 전체'에서 가장 인기 있는 가볼 만한 곳을 우선적으로 검색하세요.
    2. 날씨 제약 (Weather Constraint): 비나 눈이 온다면, 검색어에 "실내 가볼만한곳", "복합문화공간" 등 실내 활동 키워드를 최우선으로 추가하세요.
    3. 예산 제약 (Budget Balancing): 식비/활동비 예산이 빡빡하다면, 검색어에 "가성비", "저렴한 맛집", "무료 관람" 등의 키워드를 추가해 단가를 낮추세요.
    4. 사용 제한: 이 도구는 검색 지역이 한국(국내)일 때만 사용하세요.
    """
    try:
        places = search_local(query=query, display=5)
        return [{
            "name": getattr(p, "name", "이름 없음"),
            "address": getattr(p, "address", "주소 없음"),
            "category": getattr(p, "category", "분류 없음")
        } for p in places]
    except Exception as e:
        return [{"error": str(e)}]