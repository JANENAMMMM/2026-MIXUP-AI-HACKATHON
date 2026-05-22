import os
import json
from datetime import datetime, timedelta

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage

from .state import AgentState, TravelIntent
from .llm import get_llm
from src.weather import get_weather
from src.hotel.search import search_google_hotels
from src.hotel.models import HotelSearchRequest, Hotel
from src.tourist.naver_local import search_local


# ── Mock 데이터 (API 에러/키 없을 때 Fallback) ─────────────────────────
_MOCK_HOTEL = {
    "name": "부산 해운대 그랜드 호텔 (Mock)",
    "address": "부산광역시 해운대구 해운대해변로 20",
    "cost": 150000,
}

_MOCK_RESTAURANTS = [
    {"title": "해운대 암소갈비집 (Mock)", "address": "부산 해운대구 구남로 35", "category": "한식"},
    {"title": "광안리 횟집 (Mock)", "address": "부산 수영구 광안해변로 219", "category": "해산물"},
]

_MOCK_ATTRACTIONS = [
    {"title": "해운대해수욕장 (Mock)", "address": "부산 해운대구 우동", "category": "관광명소"},
    {"title": "해동용궁사 (Mock)", "address": "부산 기장군 기장읍 용궁길 86", "category": "사찰"},
]


def build_graph(model: str = "solar-pro3", temperature: float = 0.7):
    """5-노드 여행 플래너 LangGraph 그래프를 빌드하고 컴파일해 반환한다.

    파이프라인:
        START → intent_router → weather → stay → place → synthesizer → END
    """
    llm = get_llm(model=model, temperature=temperature)

    # ── Node 1: Intent Router ──────────────────────────────────────────
    def intent_router(state: AgentState) -> dict:
        """사용자 입력에서 목적지/날짜/예산/인원을 추출해 TravelIntent로 변환한다."""
        user_msg = state["messages"][-1].content
        today = datetime.now().date()

        system = SystemMessage(content=(
            "너는 여행 정보 추출 AI야. 사용자 입력에서 다음 JSON을 추출해. "
            "날짜가 'M/D' 형식이면 올해 연도를 붙여 'YYYY-MM-DD'로 변환해. "
            "인원 정보가 없으면 adults=1로 고정해. "
            "예산 단위가 '만원'이면 10000 곱해서 정수로 변환해. "
            f"오늘 날짜는 {today}야.\n\n"
            "반드시 다음 JSON 형식만 출력해 (설명 없이):\n"
            '{"destination":"부산","check_in":"2026-05-30","check_out":"2026-05-31","budget":500000,"adults":1}'
        ))

        response = llm.invoke([system, HumanMessage(content=user_msg)])
        raw = response.content.strip()

        # JSON 파싱 (LLM이 코드블록으로 감쌀 수도 있어서 정제)
        if "```" in raw:
            raw = raw.split("```")[1].strip()
            if raw.startswith("json"):
                raw = raw[4:].strip()

        data = json.loads(raw)
        intent: TravelIntent = {
            "destination": data.get("destination", "서울"),
            "check_in": data.get("check_in", today.isoformat()),
            "check_out": data.get("check_out", (today + timedelta(days=1)).isoformat()),
            "budget": int(data.get("budget", 500000)),
            "adults": int(data.get("adults", 1)),
        }
        return {"intent": intent}

    # ── Node 2: Weather ────────────────────────────────────────────────
    def weather_node(state: AgentState) -> dict:
        """체크인 날짜의 날씨를 조회해 is_rainy와 weather_summary를 설정한다."""
        intent = state["intent"]
        try:
            result = get_weather(intent["destination"], intent["check_in"])
            if result is None or result.daily is None:
                return {"is_rainy": False, "weather_summary": "날씨 정보 없음"}

            d = result.daily
            prob = d.precipitation_probability_max or 0
            rain = d.rain_sum or 0
            is_rainy = prob >= 50 or rain > 1.0

            summary = (
                f"{intent['check_in']} {intent['destination']} 날씨: "
                f"최고 {d.temp_max}°C / 최저 {d.temp_min}°C, "
                f"강수확률 {prob}%, 강우량 {rain}mm"
            )
            return {"is_rainy": is_rainy, "weather_summary": summary}
        except Exception as e:
            return {"is_rainy": False, "weather_summary": f"날씨 조회 실패: {e}"}

    # ── Node 3: Stay (Hotel) ───────────────────────────────────────────
    def stay_node(state: AgentState) -> dict:
        """SerpApi Google Hotels로 숙소를 검색하고 예산을 차감한다."""
        intent = state["intent"]
        serpapi_key = os.getenv("SERPAPI_KEY")

        if not serpapi_key:
            cost = _MOCK_HOTEL["cost"]
            return {
                "hotel_name": _MOCK_HOTEL["name"],
                "hotel_address": _MOCK_HOTEL["address"],
                "hotel_cost": cost,
                "remaining_budget": intent["budget"] - cost,
            }

        try:
            req = HotelSearchRequest(
                q=f"{intent['destination']} 호텔",
                check_in_date=intent["check_in"],
                check_out_date=intent["check_out"],
                adults=intent["adults"],
                gl="kr",
                hl="ko",
                currency="KRW",
                sort_by=3,  # 가격순
            )
            result = search_google_hotels(serpapi_key, req)

            if not result.hotels:
                raise ValueError("검색 결과 없음")

            hotel: Hotel = result.hotels[0]

            # total_rate 문자열에서 숫자 추출 (예: "₩150,000" → 150000)
            # SerpApi는 "₩149,800" 또는 "149800" 형식으로 반환
            raw_cost = hotel.total_rate or hotel.rate_per_night or "0"
            digits = "".join(filter(str.isdigit, raw_cost))
            cost = int(digits) if digits else 0
            # 자릿수가 너무 적으면(5자리 미만) 단위 오류로 판단해 0 처리
            if cost < 10000:
                cost = 0

            return {
                "hotel_name": hotel.name,
                "hotel_address": "",  # SerpApi는 주소를 별도 제공하지 않음
                "hotel_cost": cost,
                "remaining_budget": intent["budget"] - cost,
            }
        except Exception:
            cost = _MOCK_HOTEL["cost"]
            return {
                "hotel_name": _MOCK_HOTEL["name"],
                "hotel_address": _MOCK_HOTEL["address"],
                "hotel_cost": cost,
                "remaining_budget": intent["budget"] - cost,
            }

    # ── Node 4: Place (Naver Local) ────────────────────────────────────
    def place_node(state: AgentState) -> dict:
        """숙소 주변 맛집/명소를 네이버 지역 검색으로 조회한다.

        비가 오면 실내 장소(카페/박물관)로 검색어를 교체한다.
        """
        intent = state["intent"]
        dest = intent["destination"]
        is_rainy = state.get("is_rainy", False)

        restaurant_query = f"{dest} 맛집"
        attraction_query = f"{dest} 카페 박물관" if is_rainy else f"{dest} 명소 관광지"

        def _to_dict_list(places):
            return [
                {"title": p.title, "address": p.road_address or p.address, "category": p.category}
                for p in places[:2]
            ]

        try:
            restaurants = _to_dict_list(search_local(restaurant_query, display=2))
        except Exception:
            restaurants = _MOCK_RESTAURANTS

        try:
            attractions = _to_dict_list(search_local(attraction_query, display=2))
        except Exception:
            attractions = _MOCK_ATTRACTIONS

        return {"restaurants": restaurants, "attractions": attractions}

    # ── Node 5: Synthesizer ────────────────────────────────────────────
    def synthesizer_node(state: AgentState) -> dict:
        """수집된 정보를 LLM에 넘겨 동선 최적화 + 마크다운 리포트를 생성한다."""
        intent = state["intent"]

        places_text = "[ 수집된 장소 ]\n"
        places_text += f"숙소: {state.get('hotel_name')} ({state.get('hotel_address')})\n"
        for r in state.get("restaurants", []):
            places_text += f"맛집: {r['title']} | {r['address']} | {r['category']}\n"
        for a in state.get("attractions", []):
            places_text += f"명소: {a['title']} | {a['address']} | {a['category']}\n"

        system = SystemMessage(content=(
            "너는 전문 여행 플래너야. "
            "아래 [수집된 장소] 목록에 있는 장소만 사용해서 동선이 효율적인 여행 일정을 짜줘. "
            "목록에 없는 장소, 교통수단 가격, 식비, KTX 일정 등은 절대 임의로 추가하지 마. "
            "정보가 부족한 항목은 '정보 없음'으로 표기해. "
            "결과는 한국어 마크다운으로 출력하고, 예산 현황과 날씨 정보도 포함해."
        ))

        user_content = (
            f"목적지: {intent['destination']}\n"
            f"일정: {intent['check_in']} ~ {intent['check_out']}\n"
            f"예산: {intent['budget']:,}원 (숙박 후 잔여: {state.get('remaining_budget', 0):,}원)\n"
            f"날씨: {state.get('weather_summary', '')}\n\n"
            f"{places_text}"
        )

        response = llm.invoke([system, HumanMessage(content=user_content)])
        return {"final_report": response.content}

    # ── Graph 조립 ─────────────────────────────────────────────────────
    graph = StateGraph(AgentState)
    graph.add_node("intent_router", intent_router)
    graph.add_node("weather", weather_node)
    graph.add_node("stay", stay_node)
    graph.add_node("place", place_node)
    graph.add_node("synthesizer", synthesizer_node)

    graph.add_edge(START, "intent_router")
    graph.add_edge("intent_router", "weather")
    graph.add_edge("weather", "stay")
    graph.add_edge("stay", "place")
    graph.add_edge("place", "synthesizer")
    graph.add_edge("synthesizer", END)

    return graph.compile()
