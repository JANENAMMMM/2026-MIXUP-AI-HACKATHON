import json
import math
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_core.messages import HumanMessage, SystemMessage

from src.agent.state import AgentState
from src.cheapest_date.iata import get_iata, is_domestic as iata_is_domestic


# ──────────────────────────────────────────────
# 거리 계산 및 경로 최적화
# ──────────────────────────────────────────────

def _haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 간 Haversine 거리 (km)."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def _nearest_neighbor_route(
    start_lat: float, start_lng: float, places: list[dict]
) -> list[dict]:
    """최근접 이웃 그리디로 장소 방문 순서를 최적화한다."""
    unvisited = list(places)
    ordered: list[dict] = []
    cur_lat, cur_lng = start_lat, start_lng

    while unvisited:
        nearest = min(unvisited, key=lambda p: _haversine(cur_lat, cur_lng, p["lat"], p["lng"]))
        unvisited.remove(nearest)
        ordered.append(nearest)
        cur_lat, cur_lng = nearest["lat"], nearest["lng"]

    return ordered


def _get_hotel_coords(
    hotel_name: str, hotel_address: str, dest: str, domestic: bool
) -> tuple[float, float] | None:
    """호텔 좌표를 Naver/Google 검색으로 획득한다. 실패 시 None."""
    if not hotel_name or "Mock" in hotel_name:
        return None
    query = f"{dest} {hotel_name}"
    try:
        if domestic:
            from src.tourist.naver_local import search_local
            results = search_local(query, display=1)
            if results and results[0].lat and results[0].lng:
                return (results[0].lat, results[0].lng)
        else:
            from src.tourist.google_places import search_places
            results = search_places(query)
            if results and results[0].lat and results[0].lng:
                return (results[0].lat, results[0].lng)
    except Exception:
        pass
    return None


def _build_route_note(
    hotel_lat: float,
    hotel_lng: float,
    hotel_name: str,
    restaurants: list[dict],
    attractions: list[dict],
    trip_nights: int,
) -> str:
    """좌표가 있는 장소들로 일별 최적 동선 요약을 생성한다."""
    geo_tagged = [
        {**p, "_kind": "restaurant"}
        for p in restaurants
        if p.get("lat") and p.get("lng")
    ] + [
        {**p, "_kind": "attraction"}
        for p in attractions
        if p.get("lat") and p.get("lng")
    ]

    if not geo_tagged:
        return ""

    ordered = _nearest_neighbor_route(hotel_lat, hotel_lng, geo_tagged)

    days = max(1, trip_nights)
    per_day = math.ceil(len(ordered) / days)

    lines = ["[ 위치 기반 최적 동선 ]",
             f"숙소({hotel_name or '출발지'}) 기준 최근접 이웃 알고리즘으로 이동 거리를 최소화한 순서입니다.\n"]

    for d in range(days):
        day_places = ordered[d * per_day: (d + 1) * per_day]
        if not day_places:
            continue
        lines.append(f"Day {d + 1}:")
        cur_lat, cur_lng = hotel_lat, hotel_lng
        total_km = 0.0
        for p in day_places:
            dist = _haversine(cur_lat, cur_lng, p["lat"], p["lng"])
            total_km += dist
            icon = "🍽" if p["_kind"] == "restaurant" else "🏛"
            lines.append(
                f"  {icon} {p['title']} "
                f"({p.get('category', '')})"
                f"  ← 이전 위치에서 {dist:.1f}km"
            )
            cur_lat, cur_lng = p["lat"], p["lng"]
        lines.append(f"  ↳ Day {d + 1} 이동 합계: 약 {total_km:.1f}km\n")

    return "\n".join(lines)


# ──────────────────────────────────────────────
# 박수 → 목표 장소 수
# ──────────────────────────────────────────────

def _place_counts(trip_nights: int) -> tuple[int, int]:
    """(맛집 목표 수, 명소 목표 수) 반환."""
    n = max(1, trip_nights)
    r = min(n + 1, 6)       # 맛집: 2~6
    a = min(n * 2 + 1, 10)  # 명소: 3~10 (하루 2곳 페이스)
    return r, a


# ──────────────────────────────────────────────
# 검색 쿼리 풀
# ──────────────────────────────────────────────

def _build_queries(
    dest: str, is_rainy: bool, domestic: bool
) -> tuple[list[str], list[str]]:
    """(맛집 쿼리 목록, 명소 쿼리 목록) 반환 — 항상 전체 풀 반환, 박수와 무관하게 다양한 후보 확보."""
    if domestic:
        r_pool = [
            # 끼니별
            f"{dest} 아침 식사 조식 카페",
            f"{dest} 점심 맛집 로컬 식당",
            f"{dest} 저녁 식당 분위기 좋은",
            # 장르별
            f"{dest} 한식 향토 음식 노포",
            f"{dest} 해산물 횟집 생선구이",
            f"{dest} 고기 구이 삼겹살 갈비",
            f"{dest} 일식 라멘 스시",
            f"{dest} 양식 파스타 피자",
            # 분위기/테마별
            f"{dest} 감성 카페 브런치",
            f"{dest} 루프탑 뷰 카페",
            f"{dest} 파인다이닝 고급 레스토랑",
            f"{dest} 로컬 시장 길거리 음식",
        ]
        a_pool_clear = [
            # 자연·경관
            f"{dest} 자연 경관 뷰포인트 전망대",
            f"{dest} 해변 바다 산책",
            f"{dest} 공원 산책로 피크닉",
            f"{dest} 야경 명소 야간 산책",
            # 문화·역사
            f"{dest} 박물관 미술관",
            f"{dest} 역사 유적지 문화재",
            f"{dest} 전통 마을 한옥",
            # 쇼핑·시장
            f"{dest} 쇼핑 거리 상점가",
            f"{dest} 전통시장 재래시장",
            # 체험·액티비티
            f"{dest} 체험 액티비티 투어",
            f"{dest} 테마파크 놀이공원",
            f"{dest} 온천 스파 힐링",
        ]
        a_pool_rainy = [
            # 실내 문화
            f"{dest} 실내 박물관 미술관",
            f"{dest} 실내 전시회 갤러리",
            f"{dest} 전통 문화 체험관",
            # 실내 휴식
            f"{dest} 실내 카페 디저트 베이커리",
            f"{dest} 찜질방 스파 온천",
            f"{dest} 책방 독립서점",
            # 실내 쇼핑·오락
            f"{dest} 쇼핑몰 백화점",
            f"{dest} 수족관 아쿠아리움",
            f"{dest} 영화관 공연장 뮤지컬",
            f"{dest} 실내 체험관 방탈출",
            # 실내 먹거리
            f"{dest} 실내 마켓 푸드홀",
            f"{dest} 루프탑 실내 뷰 명소",
        ]
    else:
        r_pool = [
            # by meal
            f"{dest} breakfast cafes brunch spots",
            f"{dest} lunch local restaurants",
            f"{dest} dinner restaurants romantic atmosphere",
            # by cuisine
            f"{dest} local street food market",
            f"{dest} seafood traditional cuisine",
            f"{dest} fine dining rooftop restaurant",
            f"{dest} vegetarian vegan cafe",
            f"{dest} bakery dessert sweet shop",
            # by vibe
            f"{dest} hidden gem local favorite restaurant",
            f"{dest} rooftop bar food",
            f"{dest} night market food stalls",
            f"{dest} cooking class food experience",
        ]
        a_pool_clear = [
            # nature & scenery
            f"{dest} scenic viewpoints sunrise sunset",
            f"{dest} parks gardens nature walk",
            f"{dest} beaches waterfront promenade",
            f"{dest} mountain hiking trails",
            # culture & history
            f"{dest} historical landmarks monuments",
            f"{dest} museums cultural heritage",
            f"{dest} religious sites temples shrines",
            f"{dest} traditional neighborhoods old town",
            # shopping & local life
            f"{dest} local markets bazaars",
            f"{dest} shopping districts boutiques",
            # experiences & entertainment
            f"{dest} outdoor adventure activities",
            f"{dest} art districts galleries street art",
            f"{dest} nightlife entertainment",
        ]
        a_pool_rainy = [
            # indoor culture
            f"{dest} museums",
            f"{dest} art galleries exhibitions",
            f"{dest} historical indoor sites palace",
            # indoor leisure
            f"{dest} spas wellness centers",
            f"{dest} aquarium indoor attractions",
            f"{dest} theaters concert halls",
            # indoor shopping & food
            f"{dest} indoor shopping malls",
            f"{dest} indoor markets food halls",
            f"{dest} cafes bookshops cozy",
            # experiences
            f"{dest} cooking classes workshops",
            f"{dest} escape rooms entertainment center",
            f"{dest} unique indoor experiences",
        ]

    a_pool = a_pool_rainy if is_rainy else a_pool_clear
    return r_pool, a_pool


# ──────────────────────────────────────────────
# 병렬 API 호출
# ──────────────────────────────────────────────

def _search_parallel_naver(queries: list[str], display: int = 5) -> list[dict]:
    """Naver Local API 병렬 호출 → 중복 제거된 후보 목록."""
    from src.tourist.naver_local import search_local

    seen: set[str] = set()
    results: list[dict] = []

    def _fetch(q: str) -> list[dict]:
        places = search_local(q, display=display)
        return [
            {
                "title": p.title,
                "address": p.road_address or p.address,
                "category": p.category,
                "lat": p.lat,
                "lng": p.lng,
            }
            for p in places
        ]

    with ThreadPoolExecutor(max_workers=min(len(queries), 5)) as ex:
        futures = {ex.submit(_fetch, q): q for q in queries}
        for fut in as_completed(futures):
            try:
                for item in fut.result():
                    key = item["title"]
                    if key not in seen:
                        seen.add(key)
                        results.append(item)
            except Exception as e:
                print(f"  ✗ Naver 검색 실패 ({futures[fut]}): {e}")

    return results


def _search_parallel_google(queries: list[str]) -> list[dict]:
    """Google Places API 병렬 호출 → 중복 제거된 후보 목록."""
    from src.tourist.google_places import search_places

    seen: set[str] = set()
    results: list[dict] = []

    def _fetch(q: str) -> list[dict]:
        places = search_places(q)
        return [
            {"title": p.name, "address": p.address, "category": "", "lat": p.lat, "lng": p.lng}
            for p in places
        ]

    with ThreadPoolExecutor(max_workers=min(len(queries), 5)) as ex:
        futures = {ex.submit(_fetch, q): q for q in queries}
        for fut in as_completed(futures):
            try:
                for item in fut.result():
                    key = item["title"]
                    if key not in seen:
                        seen.add(key)
                        results.append(item)
            except Exception as e:
                print(f"  ✗ Google Places 검색 실패 ({futures[fut]}): {e}")

    return results


# ──────────────────────────────────────────────
# LLM 큐레이션
# ──────────────────────────────────────────────

def _curate_with_llm(
    llm,
    dest: str,
    trip_nights: int,
    is_rainy: bool,
    hotel_name: str,
    hotel_address: str,
    raw_r: list[dict],
    raw_a: list[dict],
    r_count: int,
    a_count: int,
) -> dict:
    weather_note = (
        "비 또는 눈이 내립니다. 실내 명소를 최우선으로 선택하고, 실외 장소는 꼭 필요한 경우에만 포함하세요."
        if is_rainy
        else "날씨가 좋습니다. 실내·실외 장소를 균형 있게 선택하세요."
    )

    def _fmt(places: list[dict]) -> str:
        if not places:
            return "  (검색 결과 없음)"
        return "\n".join(
            f"  - {p['title']} | {p.get('address', '')} | {p.get('category', '')}"
            for p in places
        )

    system = SystemMessage(content=(
        "너는 전문 여행 큐레이터야. 제공된 후보 목록에서 여행 일정에 최적인 장소를 선별해줘.\n\n"
        "【필수 선별 원칙】\n"
        "1. 지정된 수를 정확히 선택 — 더 많지도 적지도 않게.\n"
        "2. 다양성 최우선 — 같은 카테고리(예: 카페, 해산물) 연속 금지. "
        "맛집은 한식·양식·카페·간식 등 장르를 섞어야 함. "
        "명소는 자연·문화·체험·쇼핑·야경 등 테마를 골고루 분산.\n"
        "3. 중복 배제 — 이름이 유사하거나 같은 건물/복합시설에 있는 장소는 1곳만 선택.\n"
        "4. 날씨 지시 준수 — 비/눈이면 실내 명소 우선, 맑으면 실내·실외 균형.\n"
        "5. 동선 효율 — 숙소 기준으로 이동 동선이 효율적인 장소 우선.\n\n"
        "반드시 아래 JSON 형식만 출력 (설명·마크다운 없이):\n"
        '{"restaurants":[{"title":"...","address":"...","category":"장르(예:한식/카페/양식)","description":"한 줄 소개"}],'
        '"attractions":[{"title":"...","address":"...","category":"테마(예:자연/문화/쇼핑/체험)","description":"한 줄 소개"}]}'
    ))

    user_content = (
        f"목적지: {dest}\n"
        f"일정: {trip_nights}박\n"
        f"날씨: {weather_note}\n"
        f"숙소: {hotel_name} / {hotel_address}\n\n"
        f"[맛집·카페 후보] → {r_count}곳 선별 필요\n{_fmt(raw_r)}\n\n"
        f"[명소·체험 후보] → {a_count}곳 선별 필요\n{_fmt(raw_a)}\n\n"
        f"위 후보에서 정확히 맛집 {r_count}곳, 명소 {a_count}곳을 선별하고 "
        "각 장소마다 한 줄 소개(description)와 적절한 카테고리를 작성해줘."
    )

    response = llm.invoke([system, HumanMessage(content=user_content)])
    raw = response.content.strip()
    if "```" in raw:
        raw = raw.split("```")[1].strip()
        if raw.startswith("json"):
            raw = raw[4:].strip()

    return json.loads(raw)


# ──────────────────────────────────────────────
# Mock 폴백
# ──────────────────────────────────────────────

_MOCK_RESTAURANTS = [
    {"title": "현지 맛집 1 (Mock)", "address": "목적지 중심가", "category": "한식", "description": "현지인이 즐겨 찾는 대표 맛집"},
    {"title": "현지 카페 (Mock)", "address": "목적지 중심가", "category": "카페", "description": "분위기 좋은 로컬 카페"},
    {"title": "해산물 식당 (Mock)", "address": "목적지 해안가", "category": "해산물", "description": "신선한 해산물 전문점"},
]
_MOCK_ATTRACTIONS = [
    {"title": "대표 관광지 (Mock)", "address": "목적지 중심", "category": "관광명소", "description": "현지 대표 관광 명소"},
    {"title": "박물관 (Mock)", "address": "목적지 중심", "category": "박물관", "description": "지역 역사와 문화를 담은 박물관"},
    {"title": "자연 경관 (Mock)", "address": "목적지 외곽", "category": "자연", "description": "아름다운 자연 경관"},
    {"title": "쇼핑 거리 (Mock)", "address": "목적지 중심가", "category": "쇼핑", "description": "다양한 기념품과 로컬 상점"},
]


def _mock_for(r_count: int, a_count: int) -> tuple[list[dict], list[dict]]:
    r = (_MOCK_RESTAURANTS * 3)[:r_count]
    a = (_MOCK_ATTRACTIONS * 3)[:a_count]
    return r, a


# ──────────────────────────────────────────────
# Node 팩토리
# ──────────────────────────────────────────────

def make_place_node(llm):
    def place_node(state: AgentState) -> dict:
        intent = state["intent"]
        dest = intent["destination"]
        trip_nights = intent.get("trip_nights", 2)
        is_rainy = state.get("is_rainy", False)
        hotel_name = state.get("hotel_name", "")
        hotel_address = state.get("hotel_address", "")

        iata = get_iata(dest)
        domestic = iata_is_domestic(iata) if iata else False

        r_count, a_count = _place_counts(trip_nights)
        r_queries, a_queries = _build_queries(dest, is_rainy, domestic)

        api_label = "국내→Naver" if domestic else "해외→Google Places"
        weather_label = "☔ 실내 우선" if is_rainy else "☀ 실내·실외 균형"
        print(f"\n📍 [4/5] 장소 검색 중 — {dest} ({api_label}) | {trip_nights}박 | {weather_label}")
        print(f"  → 목표: 맛집 {r_count}곳 ({len(r_queries)}개 쿼리), 명소 {a_count}곳 ({len(a_queries)}개 쿼리)")

        # API 병렬 검색
        try:
            if domestic:
                raw_r = _search_parallel_naver(r_queries)
                raw_a = _search_parallel_naver(a_queries)
            else:
                raw_r = _search_parallel_google(r_queries)
                raw_a = _search_parallel_google(a_queries)
            print(f"  ✓ 수집된 후보: 맛집 {len(raw_r)}곳, 명소 {len(raw_a)}곳")
        except Exception as e:
            print(f"  ✗ API 검색 전체 실패 ({e}) → Mock 사용")
            raw_r, raw_a = _mock_for(r_count, a_count)

        # LLM 큐레이션
        # raw 좌표 인덱스: 제목 → (lat, lng)
        raw_coords: dict[str, tuple[float, float]] = {}
        for p in raw_r + raw_a:
            if p.get("lat") and p.get("lng"):
                raw_coords[p["title"]] = (p["lat"], p["lng"])

        if raw_r or raw_a:
            try:
                print(f"  → LLM 큐레이션 중...")
                curated = _curate_with_llm(
                    llm, dest, trip_nights, is_rainy,
                    hotel_name, hotel_address,
                    raw_r, raw_a, r_count, a_count,
                )
                restaurants = curated.get("restaurants", [])[:r_count]
                attractions = curated.get("attractions", [])[:a_count]

                # 부족한 경우 raw로 보충
                if len(restaurants) < r_count:
                    restaurants += raw_r[len(restaurants):r_count]
                if len(attractions) < a_count:
                    attractions += raw_a[len(attractions):a_count]

            except Exception as e:
                print(f"  ✗ LLM 큐레이션 실패 ({e}) → 수집 결과 직접 사용")
                restaurants = raw_r[:r_count]
                attractions = raw_a[:a_count]
        else:
            restaurants, attractions = _mock_for(r_count, a_count)

        # LLM이 큐레이션한 장소에 원본 좌표를 복원
        for p in restaurants + attractions:
            if not p.get("lat"):
                coords = raw_coords.get(p["title"])
                if coords:
                    p["lat"], p["lng"] = coords

        print(f"  ✓ 맛집: {[r['title'] for r in restaurants]}")
        print(f"  ✓ 명소: {[a['title'] for a in attractions]}")

        # 위치 기반 경로 최적화
        print(f"  → 동선 최적화 중...")
        hotel_coords = _get_hotel_coords(hotel_name, hotel_address, dest, domestic)
        if hotel_coords:
            h_lat, h_lng = hotel_coords
            print(f"  ✓ 호텔 좌표 확보: ({h_lat:.4f}, {h_lng:.4f})")
        else:
            # 좌표 있는 장소들의 중심점을 출발지로 사용
            geo = [p for p in restaurants + attractions if p.get("lat") and p.get("lng")]
            if geo:
                h_lat = sum(p["lat"] for p in geo) / len(geo)
                h_lng = sum(p["lng"] for p in geo) / len(geo)
            else:
                h_lat, h_lng = 0.0, 0.0

        route_note = _build_route_note(
            h_lat, h_lng, hotel_name, restaurants, attractions, trip_nights
        )
        if route_note:
            geo_count = sum(1 for p in restaurants + attractions if p.get("lat") and p.get("lng"))
            print(f"  ✓ 동선 계산 완료 ({geo_count}개 장소 좌표 반영)")
        else:
            print(f"  ✗ 좌표 없음 → 동선 계산 생략")

        return {"restaurants": restaurants, "attractions": attractions, "route_note": route_note}

    return place_node
