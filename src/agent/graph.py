import os
import json
from datetime import datetime, timedelta, date as date_type

from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, SystemMessage

from .state import AgentState, TravelIntent
from .llm import get_llm
from src.weather import get_weather
from src.hotel.search import search_google_hotels
from src.hotel.models import HotelSearchRequest, Hotel
from src.tourist.naver_local import search_local
from src.cheapest_date import get_cheapest_dates
from src.cheapest_date.iata import get_iata, is_domestic as iata_is_domestic


# ── Mock 데이터 ────────────────────────────────────────────────────────
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
    """6-노드 여행 플래너 LangGraph 그래프.

    날짜 확정:  START → intent_router → weather → stay → place → synthesizer → END
    날짜 미정:  START → intent_router → date_optimizer → weather → stay → place → synthesizer → END
    """
    llm = get_llm(model=model, temperature=temperature)

    # ── Node 1: Intent Router ──────────────────────────────────────────
    def intent_router(state: AgentState) -> dict:
        """자연어 입력에서 목적지/날짜/예산/인원을 추출한다.

        날짜가 명시되지 않으면 date_fixed=False로 표시해 date_optimizer로 라우팅한다.
        """
        user_msg = state["messages"][-1].content
        today = datetime.now().date()

        system = SystemMessage(content=(
            "너는 여행 정보 추출 AI야. 사용자 입력에서 아래 JSON을 추출해.\n"
            "규칙:\n"
            "- 날짜가 'M/D' 형식이면 올해 연도를 붙여 'YYYY-MM-DD'로 변환.\n"
            "- 날짜가 정확히 확정된 경우에만 date_fixed=true.\n"
            "- '7월 중', '여름에', '대충 7월', '7월쯤', '8월 초' 처럼 월이나 시기만 언급되면 "
            "date_fixed=false, target_months에 해당 월을 'YYYYMM' 형식으로 설정.\n"
            "- 날짜가 전혀 없거나 '미정'이면 date_fixed=false, target_months=[].\n"
            "- date_fixed=false면 check_in='', check_out='' 로 설정.\n"
            "- 숙박 기간이 언급되면 trip_nights에 설정 (예: '3박4일' → 3, '2박' → 2). 없으면 2.\n"
            "- 예산 단위가 '만원'이면 10000 곱해 정수로 변환.\n"
            "- 인원 정보 없으면 adults=1.\n"
            f"- 오늘 날짜: {today}\n\n"
            "반드시 아래 JSON 형식만 출력 (설명 없이):\n"
            '{"destination":"런던","date_fixed":false,"check_in":"","check_out":"",'
            '"budget":3000000,"adults":1,"trip_nights":3,"target_months":["202607"]}'
        ))

        print("\n🧠 [1/5] 의도 분석 중...")
        response = llm.invoke([system, HumanMessage(content=user_msg)])
        raw = response.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1].strip()
            if raw.startswith("json"):
                raw = raw[4:].strip()

        data = json.loads(raw)
        date_fixed: bool = bool(data.get("date_fixed", True))
        trip_nights: int = int(data.get("trip_nights", 2))

        if date_fixed:
            check_in = data.get("check_in", today.isoformat())
            check_out = data.get("check_out", (today + timedelta(days=trip_nights)).isoformat())
        else:
            check_in = ""
            check_out = ""

        target_months: list = data.get("target_months", [])

        intent: TravelIntent = {
            "destination": data.get("destination", "서울"),
            "check_in": check_in,
            "check_out": check_out,
            "budget": int(data.get("budget", 500000)),
            "adults": int(data.get("adults", 1)),
            "trip_nights": trip_nights,
            "target_months": target_months,
        }
        date_str = f"{check_in} ~ {check_out}" if date_fixed else "미정"
        print(f"  ✓ 목적지: {intent['destination']} | 날짜: {date_str} | 예산: {intent['budget']:,}원 | {trip_nights}박")
        return {"intent": intent, "date_fixed": date_fixed}

    # ── Node 2: Date Optimizer ─────────────────────────────────────────
    def date_optimizer_node(state: AgentState) -> dict:
        """항공권 최저가 + 날씨를 교차 분석해 최적 여행 날짜 TOP 3를 선정한다.

        점수 기준 (총 13점):
          - 날씨: 맑음(+3) + 적정 기온 18~28°C(+3) + 강수확률 20% 미만(+2) = 최대 8점
          - 가격: 상위 10개 중 순위 기반 0~5점
        """
        intent = state["intent"]
        dest = intent["destination"]
        trip_nights = intent["trip_nights"]
        today = datetime.now().date()

        # IATA 코드 조회
        print(f"\n🗓️  [날짜 최적화] {dest} 항공권 + 날씨 교차 분석 중...")
        iata_dest = get_iata(dest)
        if not iata_dest:
            print(f"  ✗ IATA 코드 없음: '{dest}' — 날씨 기반 추천으로 전환")
            return _weather_only_candidates(dest, trip_nights, today, intent)

        iata_origin = "ICN"
        domestic = iata_is_domestic(iata_dest)
        print(f"  → {iata_origin} → {iata_dest} ({'국내선' if domestic else '국제선'}), {trip_nights}박 기준")

        # 후보 날짜 생성: target_months 기준, 없으면 다음 달~3개월
        target_months: list = intent.get("target_months") or []
        if not target_months:
            for i in range(1, 4):
                m = (today.replace(day=1) + timedelta(days=32 * i)).replace(day=1)
                target_months.append(m.strftime("%Y%m"))

        candidate_dates = _make_candidate_dates(target_months, today)
        print(f"  → 후보 날짜 {len(candidate_dates)}개: {candidate_dates[0]} ~ {candidate_dates[-1]}")

        flights = get_cheapest_dates(
            origin=iata_origin,
            destination=iata_dest,
            candidate_dates=candidate_dates,
            trip_nights=trip_nights,
            is_domestic=domestic,
            top_n=10,
        )

        if not flights:
            print("  ✗ 항공권 조회 실패 — 날씨 기반 추천으로 전환")
            return _weather_only_candidates(dest, trip_nights, today, intent)
        print(f"  ✓ 항공권 {len(flights)}건 조회 완료")

        # 가격 점수: 순위 1위=5점, 10위=0.5점
        max_price = max(f.price for f in flights)
        min_price = min(f.price for f in flights)
        price_range = max(max_price - min_price, 1)

        candidates = []
        for flight in flights[:10]:
            try:
                w = get_weather(dest, flight.date, silent=True)
            except Exception:
                w = None

            weather_score = 0
            weather_desc = "날씨 조회 불가"
            if w and w.daily:
                d = w.daily
                prob = d.precipitation_probability_max or 0
                temp_max = d.temp_max or 20
                code = d.weather_code or 99
                if code <= 2:
                    weather_score += 3
                if 18 <= temp_max <= 28:
                    weather_score += 3
                if prob < 20:
                    weather_score += 2
                weather_desc = f"최고 {temp_max}°C, 강수확률 {prob}%"

            price_score = round((max_price - flight.price) / price_range * 5, 1)
            total_score = weather_score + price_score

            check_out = (
                datetime.strptime(flight.date, "%Y-%m-%d").date()
                + timedelta(days=trip_nights)
            ).isoformat()

            candidates.append({
                "check_in": flight.date,
                "check_out": check_out,
                "flight_price": flight.price,
                "weather_summary": weather_desc,
                "score": total_score,
                "reason": f"항공 {flight.price:,}원 · {weather_desc}",
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        top3 = candidates[:3]
        print("  ✓ 추천 날짜 TOP 3:")
        for i, c in enumerate(top3, 1):
            print(f"    {i}위) {c['check_in']} ~ {c['check_out']} | 점수 {c['score']} | {c['reason']}")

        # 1위를 intent에 반영해 이후 노드가 그대로 사용하게 함
        best = top3[0]
        updated_intent = dict(intent)
        updated_intent["check_in"] = best["check_in"]
        updated_intent["check_out"] = best["check_out"]

        return {
            "candidate_dates": top3,
            "intent": updated_intent,
            "date_fixed": True,
        }

    def _make_candidate_dates(target_months: list[str], today: date_type) -> list[str]:
        """target_months에서 4일 간격 후보 날짜 최대 8개를 생성한다."""
        from datetime import date as date_cls
        candidates = []
        for month_str in target_months:
            year, month = int(month_str[:4]), int(month_str[4:])
            d = date_cls(year, month, 1)
            while d.month == month and len(candidates) < 8:
                if (d - today).days > 7:
                    candidates.append(d.isoformat())
                d += timedelta(days=4)
        return candidates or [(today + timedelta(days=30)).isoformat()]

    def _weather_only_candidates(dest: str, trip_nights: int, today: date_type, intent: TravelIntent) -> dict:
        """항공 API 실패 시 날씨만으로 최적 날짜 3개를 추천한다.

        target_months가 있으면 해당 월의 날짜를 탐색하고,
        없으면 D+14 이내 단기 예보 범위를 탐색한다.
        """
        target_months: list = intent.get("target_months") or []
        if target_months:
            probe_dates = _make_candidate_dates(target_months, today)
        else:
            probe_dates = [(today + timedelta(days=i)).isoformat() for i in range(1, 14, 3)]

        candidates = []
        for check_date in probe_dates:
            try:
                w = get_weather(dest, check_date, silent=True)
            except Exception:
                continue
            if not w or not w.daily or w.daily.temp_max is None:
                continue
            d = w.daily
            prob = d.precipitation_probability_max
            temp_max = d.temp_max
            prob_score = 3 if (prob is None or prob < 50) else 0
            temp_score = 3 if 18 <= temp_max <= 28 else 0
            score = float(prob_score + temp_score)
            prob_str = f"강수확률 {prob:.0f}%" if prob is not None else f"강수 {d.precipitation_sum or 0:.1f}mm"
            check_out = (
                datetime.strptime(check_date, "%Y-%m-%d").date()
                + timedelta(days=trip_nights)
            ).isoformat()
            candidates.append({
                "check_in": check_date,
                "check_out": check_out,
                "flight_price": 0,
                "weather_summary": f"최고 {temp_max}°C, {prob_str}",
                "score": score,
                "reason": f"날씨 기반 추천 · 최고 {temp_max}°C, {prob_str}",
            })
            if len(candidates) >= 5:
                break

        candidates.sort(key=lambda x: x["score"], reverse=True)

        updated_intent = dict(intent)
        if candidates:
            best = candidates[0]
            updated_intent["check_in"] = best["check_in"]
            updated_intent["check_out"] = best["check_out"]
            print(f"  ✓ 날씨 기반 추천 날짜: {best['check_in']} ~ {best['check_out']} ({best['reason']})")
        else:
            # 모든 날씨 조회 실패 시 target_months 첫 번째 월 1일로 고정
            fallback = probe_dates[0] if probe_dates else (today + timedelta(days=30)).isoformat()
            updated_intent["check_in"] = fallback
            updated_intent["check_out"] = (
                datetime.strptime(fallback, "%Y-%m-%d").date() + timedelta(days=trip_nights)
            ).isoformat()
            print(f"  ⚠ 날씨 조회 실패, 기본 날짜 설정: {updated_intent['check_in']}")

        return {"candidate_dates": candidates[:3], "intent": updated_intent, "date_fixed": True}

    # ── Node 3: Weather ────────────────────────────────────────────────
    def weather_node(state: AgentState) -> dict:
        """체크인~체크아웃 전 기간 날씨를 조회한다."""
        intent = state["intent"]
        dest = intent["destination"]

        if not intent.get("check_in"):
            print(f"\n⛅ [2/5] 날씨 조회 스킵 — check_in 미확정")
            return {"is_rainy": False, "weather_summary": "날짜 미확정으로 날씨 조회 불가"}

        check_in = datetime.strptime(intent["check_in"], "%Y-%m-%d").date()
        check_out = datetime.strptime(intent["check_out"], "%Y-%m-%d").date()
        nights = (check_out - check_in).days

        print(f"\n⛅ [2/5] 날씨 조회 중 — {dest} {intent['check_in']} ~ {intent['check_out']} ({nights}박)")

        daily_summaries = []
        any_rainy = False

        for i in range(nights + 1):
            target_date = (check_in + timedelta(days=i)).isoformat()
            try:
                result = get_weather(dest, target_date, silent=True)
                if result and result.daily and result.daily.temp_max is not None:
                    d = result.daily
                    prob = d.precipitation_probability_max  # 시즌 예보는 None
                    rain = d.rain_sum or d.precipitation_sum or 0
                    if (prob is not None and prob >= 50) or rain > 1.0:
                        any_rainy = True

                    # 이용 가능한 필드만 포함
                    parts = [f"{target_date}:"]
                    parts.append(f"최고 {d.temp_max}°C / 최저 {d.temp_min}°C")
                    if prob is not None:
                        parts.append(f"강수확률 {prob:.0f}%")
                    if rain:
                        parts.append(f"강우 {rain:.1f}mm")
                    line = " ".join(parts)
                    daily_summaries.append(line)
                    print(f"  ✓ {line}")
                else:
                    print(f"  ✗ {target_date}: 예보 없음 (범위 초과)")
            except Exception as e:
                daily_summaries.append(f"{target_date}: 조회 실패")
                print(f"  ✗ {target_date}: 오류 - {e}")

        return {"is_rainy": any_rainy, "weather_summary": "\n".join(daily_summaries)}

    # ── Node 4: Stay ───────────────────────────────────────────────────
    def stay_node(state: AgentState) -> dict:
        intent = state["intent"]
        serpapi_key = os.getenv("SERPAPI_KEY")

        print(f"\n🏨 [3/5] 숙소 검색 중 — {intent['destination']} {intent['check_in']} ~ {intent['check_out']}")

        if not serpapi_key:
            print("  ✗ SERPAPI_KEY 없음 → Mock 데이터 사용")
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
                gl="kr", hl="ko", currency="KRW", sort_by=3,
            )
            result = search_google_hotels(serpapi_key, req)
            if not result.hotels:
                raise ValueError("검색 결과 없음")

            hotel: Hotel = result.hotels[0]
            raw_cost = hotel.total_rate or hotel.rate_per_night or "0"
            digits = "".join(filter(str.isdigit, raw_cost))
            cost = int(digits) if digits else 0
            if cost < 10000:
                cost = 0

            print(f"  ✓ {hotel.name} | 원본 가격 문자열: '{raw_cost}' → {cost:,}원 | 잔여: {intent['budget']-cost:,}원")
            return {
                "hotel_name": hotel.name,
                "hotel_address": "",
                "hotel_cost": cost,
                "remaining_budget": intent["budget"] - cost,
            }
        except Exception as e:
            print(f"  ✗ SerpApi 실패 ({e}) → Mock 데이터 사용")
            cost = _MOCK_HOTEL["cost"]
            return {
                "hotel_name": _MOCK_HOTEL["name"],
                "hotel_address": _MOCK_HOTEL["address"],
                "hotel_cost": cost,
                "remaining_budget": intent["budget"] - cost,
            }

    # ── Node 5: Place ──────────────────────────────────────────────────
    def place_node(state: AgentState) -> dict:
        """국내 → Naver Local API / 해외 → Google Places API 자동 분기."""
        intent = state["intent"]
        dest = intent["destination"]
        is_rainy = state.get("is_rainy", False)

        iata = get_iata(dest)
        domestic = iata_is_domestic(iata) if iata else False

        print(f"\n📍 [4/5] 장소 검색 중 — {dest} ({'국내→Naver' if domestic else '해외→Google Places'})")

        if domestic:
            # ── 국내: Naver Local ──────────────────────────────────────
            r_query = f"{dest} 맛집"
            a_query = f"{dest} 카페 박물관" if is_rainy else f"{dest} 명소 관광지"

            def _naver(places):
                return [
                    {"title": p.title, "address": p.road_address or p.address, "category": p.category}
                    for p in places[:2]
                ]

            print(f"  → 맛집: '{r_query}' / 명소: '{a_query}'")
            try:
                restaurants = _naver(search_local(r_query, display=2))
            except Exception as e:
                print(f"  ✗ 맛집 Naver 실패 ({e}) → Mock 사용")
                restaurants = _MOCK_RESTAURANTS

            try:
                attractions = _naver(search_local(a_query, display=2))
            except Exception as e:
                print(f"  ✗ 명소 Naver 실패 ({e}) → Mock 사용")
                attractions = _MOCK_ATTRACTIONS

        else:
            # ── 해외: Google Places ────────────────────────────────────
            from src.tourist.google_places import search_places

            r_query = f"{dest} best restaurants"
            a_query = f"{dest} indoor museum cafe" if is_rainy else f"{dest} tourist attractions"

            def _google(places):
                return [
                    {"title": p.name, "address": p.address, "category": ""}
                    for p in places[:2]
                ]

            print(f"  → 맛집: '{r_query}' / 명소: '{a_query}'")
            try:
                restaurants = _google(search_places(r_query))
            except Exception as e:
                print(f"  ✗ 맛집 Google Places 실패 ({e})")
                restaurants = []

            try:
                attractions = _google(search_places(a_query))
            except Exception as e:
                print(f"  ✗ 명소 Google Places 실패 ({e})")
                attractions = []

        print(f"  ✓ 맛집: {[r['title'] for r in restaurants]}")
        print(f"  ✓ 명소: {[a['title'] for a in attractions]}")
        return {"restaurants": restaurants, "attractions": attractions}

    # ── Node 6: Synthesizer ────────────────────────────────────────────
    def synthesizer_node(state: AgentState) -> dict:
        intent = state["intent"]
        candidates = state.get("candidate_dates", [])

        # 날짜 최적화 결과가 있으면 리포트에 포함
        candidate_text = ""
        if candidates:
            candidate_text = "\n[ 추천 날짜 TOP 3 ]\n"
            for i, c in enumerate(candidates, 1):
                candidate_text += (
                    f"  {i}위) {c['check_in']} ~ {c['check_out']} "
                    f"| 점수 {c['score']} | {c['reason']}\n"
                )

        places_text = "[ 수집된 장소 ]\n"
        places_text += f"숙소: {state.get('hotel_name')} ({state.get('hotel_address')})\n"
        for r in state.get("restaurants", []):
            places_text += f"맛집: {r['title']} | {r['address']} | {r['category']}\n"
        for a in state.get("attractions", []):
            places_text += f"명소: {a['title']} | {a['address']} | {a['category']}\n"

        system = SystemMessage(content=(
            "너는 전문 여행 플래너야. "
            "[수집된 장소] 목록에 있는 장소만 사용해서 동선이 효율적인 여행 일정을 짜줘. "
            "목록에 없는 장소, 교통수단 가격, 식비, KTX 일정 등은 절대 임의로 추가하지 마. "
            "정보가 부족한 항목은 '정보 없음'으로 표기해. "
            "결과는 한국어 마크다운으로 출력하고, 예산 현황과 날씨 정보도 포함해."
        ))

        user_content = (
            f"목적지: {intent['destination']}\n"
            f"일정: {intent['check_in']} ~ {intent['check_out']}\n"
            f"예산: {intent['budget']:,}원 (숙박 후 잔여: {state.get('remaining_budget', 0):,}원)\n"
            f"날씨: {state.get('weather_summary', '')}\n"
            f"{candidate_text}\n"
            f"{places_text}"
        )

        print(f"\n📝 [5/5] 일정 생성 중 — Solar Pro3 호출...")
        response = llm.invoke([system, HumanMessage(content=user_content)])
        print("  ✓ 완료\n")
        return {"final_report": response.content}

    # ── Graph 조립 ─────────────────────────────────────────────────────
    def _route_after_intent(state: AgentState) -> str:
        """날짜 확정 여부에 따라 date_optimizer 또는 weather로 분기한다."""
        return "weather" if state.get("date_fixed", True) else "date_optimizer"

    graph = StateGraph(AgentState)
    graph.add_node("intent_router", intent_router)
    graph.add_node("date_optimizer", date_optimizer_node)
    graph.add_node("weather", weather_node)
    graph.add_node("stay", stay_node)
    graph.add_node("place", place_node)
    graph.add_node("synthesizer", synthesizer_node)

    graph.add_edge(START, "intent_router")
    graph.add_conditional_edges(
        "intent_router",
        _route_after_intent,
        {"weather": "weather", "date_optimizer": "date_optimizer"},
    )
    graph.add_edge("date_optimizer", "weather")
    graph.add_edge("weather", "stay")
    graph.add_edge("stay", "place")
    graph.add_edge("place", "synthesizer")
    graph.add_edge("synthesizer", END)

    return graph.compile()
