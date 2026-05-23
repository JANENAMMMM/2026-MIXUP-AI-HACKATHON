# -*- coding: utf-8 -*-
import os
import re as _re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, date as date_type

from langgraph.types import interrupt

from src.agent.state import AgentState, TravelIntent
from src.weather.forecast import get_archive, get_forecast, get_seasonal
from src.weather.geocoding import get_coordinates
from src.weather.models import DailyWeather
from src.cheapest_date import get_cheapest_dates
from src.cheapest_date.flight_crawler import _serpapi_fetch_flight
from src.cheapest_date.models import FlightPrice
from src.cheapest_date.iata import get_iata, is_domestic as iata_is_domestic

# 도시별 좌표 캐시 — 같은 도시를 여러 번 조회해도 Nominatim 호출 1회
_coord_cache: dict[str, tuple[float, float, str]] = {}

def _get_cached_coords(city: str) -> tuple[float, float, str]:
    """(lat, lon, timezone) — 첫 호출만 Nominatim에 요청하고 이후는 캐시 반환."""
    if city not in _coord_cache:
        lat, lon, _name, _country, tz = get_coordinates(city)
        _coord_cache[city] = (lat, lon, tz)
    return _coord_cache[city]

_AIRLINE_NAMES: dict[str, str] = {
    "KE": "대한항공", "OZ": "아시아나", "7C": "제주항공", "LJ": "진에어",
    "TW": "티웨이", "ZE": "이스타항공", "BX": "에어부산", "RS": "에어서울",
    "MM": "피치항공", "GK": "젯스타재팬", "BC": "스카이마크",
    "EY": "에티하드", "QR": "카타르항공", "EK": "에미레이트", "TK": "터키항공",
    "LH": "루프트한자", "AF": "에어프랑스", "BA": "영국항공", "KL": "KLM",
    "NH": "전일본공수", "JL": "일본항공", "CA": "중국국제항공",
    "MU": "중국동방항공", "CX": "캐세이패시픽", "SQ": "싱가포르항공",
    "TG": "타이항공", "AA": "아메리칸항공", "DL": "델타항공",
    "UA": "유나이티드항공", "AC": "에어캐나다", "FI": "아이슬란드항공",
    "SK": "스칸디나비아항공", "AY": "핀에어", "IB": "이베리아항공",
    "LX": "스위스항공", "OS": "오스트리아항공", "ET": "에티오피아항공",
    "MS": "이집트항공", "RJ": "요르단항공",
}

_TIME_LABEL: dict[str, str] = {
    "DAWN": "새벽", "MORNING": "오전", "AFTERNOON": "오후",
    "EVENING": "저녁", "NIGHT": "야간",
}

_TIME_PENALTY: dict[str, float] = {
    "DAWN": -3.0, "NIGHT": -2.0, "EVENING": -1.0,
    "MORNING": 0.0, "AFTERNOON": 0.0,
}


def _airline_label(codes: list[str]) -> str:
    if not codes:
        return "-"
    names = [_AIRLINE_NAMES.get(c, c) for c in codes[:2]]
    return "/".join(names)


def _enrich_with_serpapi_times(candidates: list[dict], iata_origin: str, iata_dest: str) -> None:
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return
    for c in candidates:
        try:
            info = _serpapi_fetch_flight(iata_origin, iata_dest, c["check_in"], c["check_out"], api_key)
            if info:
                if info.get("departure_time"):
                    c["departure_time"] = info["departure_time"]
                if info.get("arrival_time"):
                    c["arrival_time"] = info["arrival_time"]
                if info.get("airline_codes") and not c.get("airline_codes"):
                    c["airline_codes"] = info["airline_codes"]
                    c["airline_name"] = _airline_label(info["airline_codes"])
        except Exception:
            pass


def _make_candidate_dates(target_months: list[str], today: date_type) -> list[str]:
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
    target_months: list = intent.get("target_months") or []
    probe_dates = _make_candidate_dates(target_months, today) if target_months else [
        (today + timedelta(days=i)).isoformat() for i in range(1, 14, 3)
    ]

    try:
        _get_cached_coords(dest)
    except Exception:
        pass

    def _probe_one(check_date: str) -> dict | None:
        check_out = (datetime.strptime(check_date, "%Y-%m-%d").date() + timedelta(days=trip_nights)).isoformat()
        weather_score, weather_desc, weather_full = _get_trip_weather(dest, check_date, check_out)
        if not weather_desc or weather_desc == "날씨 조회 불가":
            return None
        return {
            "check_in": check_date, "check_out": check_out,
            "flight_price": 0, "weather_summary": weather_desc, "weather_full": weather_full,
            "score": round(weather_score, 2), "reason": f"날씨 기반 추천 · {weather_desc}",
        }

    candidates = []
    with ThreadPoolExecutor(max_workers=min(len(probe_dates), 5)) as ex:
        futs = {ex.submit(_probe_one, d): d for d in probe_dates}
        for fut in as_completed(futs):
            result = fut.result()
            if result:
                candidates.append(result)

    candidates.sort(key=lambda x: x["score"], reverse=True)
    updated_intent = dict(intent)
    weather_summary = ""
    if candidates:
        best = candidates[0]
        updated_intent["check_in"] = best["check_in"]
        updated_intent["check_out"] = best["check_out"]
        weather_summary = best.get("weather_full", best.get("weather_summary", ""))
        print(f"  ✓ 날씨 기반 추천: {best['check_in']} ~ {best['check_out']} ({best['reason']})")
    else:
        fallback = probe_dates[0] if probe_dates else (today + timedelta(days=30)).isoformat()
        updated_intent["check_in"] = fallback
        updated_intent["check_out"] = (
            datetime.strptime(fallback, "%Y-%m-%d").date() + timedelta(days=trip_nights)
        ).isoformat()
        print(f"  ⚠ 날씨 조회 실패, 기본 날짜 설정: {updated_intent['check_in']}")

    return {"candidate_dates": [], "intent": updated_intent, "date_fixed": True, "weather_summary": weather_summary}


def _get_trip_weather(dest: str, check_in: str, check_out: str) -> tuple[float, str, str]:
    """여행 기간 날씨를 한 번의 API 호출로 조회한다 (좌표 캐싱 + 날짜 범위 배치)."""
    check_in_d = datetime.strptime(check_in, "%Y-%m-%d").date()
    check_out_d = datetime.strptime(check_out, "%Y-%m-%d").date()
    nights = (check_out_d - check_in_d).days
    today = datetime.now().date()
    delta = (check_in_d - today).days

    try:
        lat, lon, tz = _get_cached_coords(dest)
        if delta < 0:
            raw = get_archive(lat, lon, check_in_d, check_out_d, tz)
        elif delta <= 16:
            raw = get_forecast(lat, lon, check_out_d, tz)
        else:
            raw = get_seasonal(lat, lon, check_in_d, check_out_d, tz)
        daily_data = raw["daily"]
    except Exception:
        return 0.0, "날씨 조회 불가", ""

    daily_lines: list[str] = []
    temp_maxes: list[float] = []
    total_rain: float = 0.0
    weather_score: float = 0.0
    n_days = 0

    for i in range(nights + 1):
        target = (check_in_d + timedelta(days=i)).isoformat()
        d = DailyWeather.from_api_response(daily_data, target)
        if d.temp_max is None:
            continue

        prob = d.precipitation_probability_max
        temp_max = d.temp_max or 20
        rain = d.rain_sum or d.precipitation_sum or 0
        code = d.weather_code or 99
        n_days += 1
        temp_maxes.append(temp_max)
        total_rain += rain

        if code <= 2:
            weather_score += 3
        elif code == 3:
            weather_score += 2
        elif code < 60:
            weather_score += 1
        if 18 <= temp_max <= 28:
            weather_score += 1
        if prob is not None and prob < 20:
            weather_score += 1

        parts = [f"{target}:"]
        parts.append(f"최고 {temp_max}°C / 최저 {d.temp_min or 0:.1f}°C")
        if prob is not None:
            parts.append(f"강수확률 {prob:.0f}%")
        if rain:
            parts.append(f"강우 {rain:.1f}mm")
        daily_lines.append(" ".join(parts))

    if n_days > 0:
        weather_score = round(weather_score / n_days, 2)

    if temp_maxes:
        t_min_val = min(temp_maxes)
        t_max_val = max(temp_maxes)
        temp_range = f"{t_min_val:.0f}~{t_max_val:.0f}°C" if t_min_val != t_max_val else f"{t_max_val:.0f}°C"
        rain_str = f" 강수 {total_rain:.1f}mm" if total_rain > 0 else " 강수 없음"
        weather_desc = f"최고 {temp_range}{rain_str}"
    else:
        weather_desc = "날씨 조회 불가"

    return weather_score, weather_desc, "\n".join(daily_lines)


def _score_flight(
    flight: FlightPrice,
    flights: list[FlightPrice],
    weather_score: float,
    prefer_nonstop: bool,
) -> tuple[float, str]:
    max_price = max(f.price for f in flights)
    min_price = min(f.price for f in flights)
    price_range = max_price - min_price
    price_score = 2.5 if price_range == 0 else round((max_price - flight.price) / price_range * 5, 2)

    stops_factor = 4.0 if prefer_nonstop else 2.0
    stops_penalty = flight.stops * stops_factor

    tc = (flight.time_category or "").upper()
    time_penalty = _TIME_PENALTY.get(tc, 0.0)
    total = price_score + weather_score - stops_penalty + time_penalty

    time_label = _TIME_LABEL.get(tc, "시간미정")
    stops_label = "직항" if flight.stops == 0 else f"경유 {flight.stops}회"
    reason = f"항공(1인/왕복) {flight.price:,}원 · {stops_label} · {time_label}"
    return round(total, 2), reason


def _display_top10(candidates: list[dict], dest: str, trip_nights: int) -> None:
    print(f"\n{'─'*90}")
    print(f"  🗓️  {dest} 왕복 항공권 추천 TOP {len(candidates)} ({trip_nights}박 기준, 가격은 왕복 1인 기준)")
    print(f"  ☔ = 강수량 20mm 초과 주의")
    print(f"{'─'*90}")
    print(f"  {'No':>2}  {'출발':^10}  {'귀국':^10}  {'출발→도착':^13}  {'항공사':<12}  {'왕복가격':>11}  {'경유':^6}  {'추천'}")
    print(f"  {'─'*2}  {'─'*10}  {'─'*10}  {'─'*13}  {'─'*12}  {'─'*11}  {'─'*6}  {'─'*4}")

    for i, c in enumerate(candidates, 1):
        stops_label = "직항" if c.get("stops", 1) == 0 else f"경유{c.get('stops', 1)}회"
        airline = c.get("airline_name") or _airline_label(c.get("airline_codes", []))

        dep_time = c.get("departure_time", "")
        arr_time = c.get("arrival_time", "")
        if dep_time:
            dep_str = dep_time.split(" ")[-1]
            arr_str = arr_time.split(" ")[-1] if arr_time else "?"
            time_str = f"{dep_str}→{arr_str}"
        else:
            tc = (c.get("time_category") or "").upper()
            time_str = _TIME_LABEL.get(tc, "시간미정")

        price_str = f"{c['flight_price']:,}원" if c["flight_price"] else "-"
        weather_short = c.get("weather_summary", "")
        ret_short = c.get("check_out", "?")[5:]

        rain_m = _re.search(r"강수 ([\d.]+)mm", weather_short)
        rain_total = float(rain_m.group(1)) if rain_m else 0.0
        rain_warn = " ☔" if rain_total > 20 else ""

        star = "★★★" if i == 1 else ("★★" if i <= 3 else "★")

        print(
            f"  {i:>2}  {c['check_in']:^10}  {ret_short:^10}  {time_str:^13}  {airline:<12}  "
            f"{price_str:>11}  {stops_label:^6}  {star}{rain_warn}"
        )
        print(f"      날씨: {weather_short}")
    print(f"{'─'*90}")


# ── date_compute: 비싼 연산(API 호출)을 모두 처리하고 state에 저장 ──────────────

def make_date_compute_node():
    def date_compute_node(state: AgentState) -> dict:
        intent = state["intent"]
        dest = intent["destination"]
        trip_nights = intent["trip_nights"]
        prefer_nonstop: bool = intent.get("prefer_nonstop", False)
        date_fixed: bool = state.get("date_fixed", False)
        today = datetime.now().date()

        if date_fixed:
            print(f"\n✈️  [항공 조회] {dest} {intent['check_in']} ~ {intent['check_out']} (날짜 확정)")
        else:
            print(f"\n🗓️  [날짜 최적화] {dest} 항공권 + 날씨 교차 분석 중...")
        if prefer_nonstop:
            print("  → 직항 선호 모드: 경유 감점 2배 적용")

        iata_dest = get_iata(dest)
        if not iata_dest or iata_is_domestic(iata_dest):
            label = "IATA 코드 없음" if not iata_dest else "국내선"
            print(f"  ✗ {label} — 날씨 기반 추천으로 전환")
            return _weather_only_candidates(dest, trip_nights, today, intent)

        iata_origin = "ICN"
        print(f"  → {iata_origin} → {iata_dest} (국제선), {trip_nights}박 기준")

        if date_fixed:
            top10 = _fixed_date_search(intent, dest, trip_nights, iata_origin, iata_dest)
        else:
            target_months: list = intent.get("target_months") or []
            if not target_months:
                for i in range(1, 4):
                    m = (today.replace(day=1) + timedelta(days=32 * i)).replace(day=1)
                    target_months.append(m.strftime("%Y%m"))
            top10 = _flexible_search(intent, dest, trip_nights, prefer_nonstop, target_months, iata_origin, iata_dest, today)

        if top10 is None:
            print("  ✗ 항공권 조회 실패 — 날씨 기반 추천으로 전환")
            return _weather_only_candidates(dest, trip_nights, today, intent)

        # 출발 시각 없는 항목 SerpAPI로 보충
        no_time = [c for c in top10 if not c.get("departure_time")]
        if no_time:
            print(f"  → 출발 시각 보완 중 ({len(no_time)}건)...")
            _enrich_with_serpapi_times(no_time, iata_origin, iata_dest)

        _display_top10(top10, dest, trip_nights)
        return {"candidate_dates": top10}

    return date_compute_node


def _fixed_date_search(
    intent: dict, dest: str, trip_nights: int, iata_origin: str, iata_dest: str
) -> list[dict] | None:
    """사용자가 날짜를 확정한 경우: SerpAPI로 해당 날짜 항공편을 직접 조회한다."""
    check_in = intent["check_in"]
    check_out = intent["check_out"]
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        print("  △ SERPAPI_KEY 없음 — 항공편 조회 생략")
        return []  # 빈 리스트: date_select에서 intent 그대로 진행

    print(f"  → SerpAPI 항공편 조회 중 ({check_in} → {check_out})...")
    info = _serpapi_fetch_flight(iata_origin, iata_dest, check_in, check_out, api_key)
    if not info or not info["price"]:
        print("  ✗ 해당 날짜 항공편 정보 없음")
        return []

    weather_score, weather_desc, weather_full = _get_trip_weather(dest, check_in, check_out)
    fake_flight = FlightPrice(
        date=check_in, return_date=check_out,
        price=info["price"], stops=0,
        airline_codes=info["airline_codes"],
        departure_time=info["departure_time"],
        arrival_time=info["arrival_time"],
        trip_days=trip_nights + 1,
    )
    total_score, reason = _score_flight(fake_flight, [fake_flight], weather_score, intent.get("prefer_nonstop", False))
    print(f"  ✓ 항공편 조회 완료: {info['price']:,}원 ({_airline_label(info['airline_codes'])})")
    return [{
        "check_in": check_in, "check_out": check_out,
        "flight_price": info["price"],
        "weather_summary": weather_desc, "weather_full": weather_full,
        "score": total_score, "reason": reason,
        "stops": 0, "time_category": "",
        "airline_codes": info["airline_codes"],
        "airline_name": _airline_label(info["airline_codes"]),
        "departure_time": info.get("departure_time", ""),
        "arrival_time": info.get("arrival_time", ""),
    }]


def _flexible_search(
    intent: dict, dest: str, trip_nights: int, prefer_nonstop: bool,
    target_months: list, iata_origin: str, iata_dest: str, today: date_type,
) -> list[dict] | None:
    """날짜 미정 시: 월별 최저가 탐색 + 날씨 교차 분석으로 TOP 10 후보를 생성한다."""
    flights = get_cheapest_dates(
        origin=iata_origin, destination=iata_dest,
        months=target_months, trip_days=[trip_nights + 1], top_n=50,
    )
    if not flights:
        return None

    print(f"  ✓ 항공권 {len(flights)}건 조회 완료 (성인 1인 왕복 기준)")

    # 1단계: 가격/경유/시간 사전 점수 → 상위 N건만 날씨 조회
    _WEATHER_TOP_N = 20
    pre_scored = []
    for flight in flights:
        pre_score, _ = _score_flight(flight, flights, 0.0, prefer_nonstop)
        check_out = (datetime.strptime(flight.date, "%Y-%m-%d").date() + timedelta(days=trip_nights)).isoformat()
        pre_scored.append((pre_score, flight, check_out))
    pre_scored.sort(key=lambda x: x[0], reverse=True)
    top_flights = pre_scored[:_WEATHER_TOP_N]

    n_weather = len(top_flights)
    label = f"상위 {n_weather}건" if len(flights) > n_weather else f"{n_weather}건 전체"
    print(f"  → {label} 날씨 조회 중...")

    # 2단계: 날씨 포함 최종 점수 — 후보 전체를 병렬로 조회
    # 먼저 좌표를 미리 캐싱해둠 (스레드 풀 내부에서 Nominatim 중복 호출 방지)
    try:
        _get_cached_coords(dest)
    except Exception:
        pass

    def _score_with_weather(flight: FlightPrice, check_out: str) -> dict:
        weather_score, weather_desc, weather_full = _get_trip_weather(dest, flight.date, check_out)
        total_score, reason = _score_flight(flight, flights, weather_score, prefer_nonstop)
        return {
            "check_in": flight.date, "check_out": check_out,
            "flight_price": flight.price,
            "weather_summary": weather_desc, "weather_full": weather_full,
            "score": total_score, "reason": reason,
            "stops": flight.stops, "time_category": flight.time_category,
            "airline_codes": flight.airline_codes,
            "airline_name": _airline_label(flight.airline_codes),
            "departure_time": getattr(flight, "departure_time", ""),
            "arrival_time": getattr(flight, "arrival_time", ""),
        }

    candidates = []
    with ThreadPoolExecutor(max_workers=min(n_weather, 8)) as ex:
        futs = {ex.submit(_score_with_weather, flight, check_out): None
                for _, flight, check_out in top_flights}
        for fut in as_completed(futs):
            try:
                candidates.append(fut.result())
            except Exception:
                pass

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates[:10]


# ── date_select: interrupt만 처리 (재실행돼도 비싼 API 없음) ────────────────────

def make_date_select_node():
    def date_select_node(state: AgentState) -> dict:
        intent = state["intent"]
        top10 = state.get("candidate_dates", [])

        if not top10:
            # 날씨 fallback이나 API 실패 시 → date_compute에서 이미 intent 설정됨
            print(f"  △ 항공편 후보 없음 — 기존 날짜/날씨 기반 일정으로 진행")
            return {"date_fixed": True}

        dest = intent["destination"]
        trip_nights = intent["trip_nights"]

        # 테이블은 date_compute에서 이미 출력됨 → 번호 선택만
        choice_str = interrupt({
            "type": "date_selection",
            "question": f"{dest} 여행 날짜를 선택해주세요:",
            "candidates": [
                {
                    "check_in": c["check_in"], "check_out": c["check_out"],
                    "weather_summary": c["weather_summary"],
                    "flight_price": c["flight_price"],
                    "score": c["score"], "reason": c["reason"],
                    "airline_name": c.get("airline_name", ""),
                    "stops": c.get("stops", -1),
                }
                for c in top10
            ],
        })

        try:
            selected_idx = int(str(choice_str)) - 1
            if not (0 <= selected_idx < len(top10)):
                selected_idx = 0
        except (ValueError, TypeError):
            selected_idx = 0

        selected = top10[selected_idx]

        dep = selected.get("departure_time", "")
        arr = selected.get("arrival_time", "")
        time_str = f" ({dep.split()[-1]} → {arr.split()[-1]})" if dep and arr else ""
        print(f"\n  ✓ 선택된 날짜: {selected['check_in']} ~ {selected['check_out']} | {selected['reason']}{time_str}")

        updated_intent = dict(intent)
        updated_intent["check_in"] = selected["check_in"]
        updated_intent["check_out"] = selected["check_out"]
        # Naver/SerpAPI 모두 1인 왕복 기준 → adults 곱해 총 항공비 산출
        updated_intent["flight_cost"] = selected["flight_price"] * updated_intent.get("adults", 1)

        full_weather = selected.get("weather_full", "")
        is_rainy = any(
            _re.search(r"강우 ([0-9.]+)mm", line) and
            float(_re.search(r"강우 ([0-9.]+)mm", line).group(1)) > 1.0
            for line in full_weather.splitlines() if line
        )

        return {
            "candidate_dates": top10[:3],
            "intent": updated_intent,
            "date_fixed": True,
            "weather_summary": full_weather,
            "is_rainy": is_rainy,
        }

    return date_select_node
