# -*- coding: utf-8 -*-
import os
from datetime import datetime, timedelta, date as date_type

from src.agent.state import AgentState, TravelIntent
from src.weather import get_weather
from src.cheapest_date import get_cheapest_dates
from src.cheapest_date.models import FlightPrice
from src.cheapest_date.iata import get_iata, is_domestic as iata_is_domestic

# 항공사 IATA 코드 → 한글 이름
_AIRLINE_NAMES: dict[str, str] = {
    "KE": "대한항공", "OZ": "아시아나", "7C": "제주항공", "LJ": "진에어",
    "TW": "티웨이", "ZE": "이스타항공", "BX": "에어부산", "RS": "에어서울",
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

# 시간대 한글 레이블
_TIME_LABEL: dict[str, str] = {
    "DAWN": "새벽",
    "MORNING": "오전",
    "AFTERNOON": "오후",
    "EVENING": "저녁",
    "NIGHT": "야간",
}

# 시간대별 감점
_TIME_PENALTY: dict[str, float] = {
    "DAWN": -3.0,
    "NIGHT": -2.0,
    "EVENING": -1.0,
    "MORNING": 0.0,
    "AFTERNOON": 0.0,
}


def _airline_label(codes: list[str]) -> str:
    """['EY', 'KE'] → '에티하드/대한항공' (최대 2개)"""
    if not codes:
        return "-"
    names = [_AIRLINE_NAMES.get(c, c) for c in codes[:2]]
    return "/".join(names)


def _enrich_with_serpapi_times(
    candidates: list[dict],
    iata_origin: str,
    iata_dest: str,
) -> None:
    """SerpAPI google_flights로 각 후보의 출발/도착 시각을 채운다 (in-place).

    실패하거나 키가 없으면 해당 항목을 빈 문자열로 둔다.
    """
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        return

    import requests
    url = "https://serpapi.com/search.json"

    print(f"  → 상위 {len(candidates)}건 출발/도착 시각 조회 중 (SerpAPI)...")
    for c in candidates:
        params = {
            "engine": "google_flights",
            "departure_id": iata_origin,
            "arrival_id": iata_dest,
            "outbound_date": c["check_in"],
            "return_date": c["check_out"],
            "currency": "KRW",
            "hl": "ko",
            "api_key": api_key,
        }
        try:
            resp = requests.get(url, params=params, timeout=12)
            resp.raise_for_status()
            data = resp.json()

            # best_flights 또는 other_flights 첫 번째 항공편
            for bucket in ("best_flights", "other_flights"):
                items = data.get(bucket, [])
                if not items:
                    continue
                legs = items[0].get("flights", [])
                if not legs:
                    continue
                first_leg = legs[0]
                last_leg = legs[-1]
                c["departure_time"] = first_leg.get("departure_airport", {}).get("time", "")
                c["arrival_time"] = last_leg.get("arrival_airport", {}).get("time", "")
                # SerpAPI airline 정보로 항공사 이름 보완
                airline_name = first_leg.get("airline", "")
                if airline_name:
                    c["airline_name"] = airline_name
                break
        except Exception:
            pass  # 실패해도 시간 없이 표시


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
            datetime.strptime(check_date, "%Y-%m-%d").date() + timedelta(days=trip_nights)
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
    weather_summary = ""
    if candidates:
        best = candidates[0]
        updated_intent["check_in"] = best["check_in"]
        updated_intent["check_out"] = best["check_out"]
        _, __, weather_full = _get_trip_weather(dest, best["check_in"], best["check_out"])
        weather_summary = weather_full
        print(f"  ✓ 날씨 기반 추천 날짜: {best['check_in']} ~ {best['check_out']} ({best['reason']})")
    else:
        fallback = probe_dates[0] if probe_dates else (today + timedelta(days=30)).isoformat()
        updated_intent["check_in"] = fallback
        updated_intent["check_out"] = (
            datetime.strptime(fallback, "%Y-%m-%d").date() + timedelta(days=trip_nights)
        ).isoformat()
        print(f"  ⚠ 날씨 조회 실패, 기본 날짜 설정: {updated_intent['check_in']}")

    return {
        "candidate_dates": candidates[:3],
        "intent": updated_intent,
        "date_fixed": True,
        "weather_summary": weather_summary,
    }


def _get_trip_weather(
    dest: str, check_in: str, check_out: str
) -> tuple[float, str, str]:
    """여행 전 기간 날씨를 조회해 (점수, 표 요약, 전체 텍스트)를 반환한다.

    Returns:
        weather_score: 날씨 점수 (0~5)
        weather_desc:  TOP 10 표에 표시할 한 줄 요약 (예: "최고 22-24°C 강수 3.5mm")
        weather_full:  weather_node 재사용용 전체 일별 텍스트
    """
    check_in_d = datetime.strptime(check_in, "%Y-%m-%d").date()
    check_out_d = datetime.strptime(check_out, "%Y-%m-%d").date()
    nights = (check_out_d - check_in_d).days

    daily_lines: list[str] = []
    temp_maxes: list[float] = []
    total_rain: float = 0.0
    weather_score: float = 0.0
    n_days = 0

    for i in range(nights + 1):
        target = (check_in_d + timedelta(days=i)).isoformat()
        try:
            w = get_weather(dest, target, silent=True)
        except Exception:
            continue
        if not w or not w.daily or w.daily.temp_max is None:
            continue

        d = w.daily
        prob = d.precipitation_probability_max
        temp_max = d.temp_max or 20
        rain = d.rain_sum or d.precipitation_sum or 0
        code = d.weather_code or 99
        n_days += 1
        temp_maxes.append(temp_max)
        total_rain += rain

        # 일별 점수 누적
        # code 0-2: 맑음(+3), 3: 약간 흐림(+2), 45-57: 안개/이슬비(+1), 그 외 비/눈(0)
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

    # 평균 점수
    if n_days > 0:
        weather_score = round(weather_score / n_days, 2)

    # 한 줄 요약 (표용)
    if temp_maxes:
        t_min_val = min(temp_maxes)
        t_max_val = max(temp_maxes)
        temp_range = f"{t_min_val:.0f}~{t_max_val:.0f}°C" if t_min_val != t_max_val else f"{t_max_val:.0f}°C"
        rain_str = f" 강수 {total_rain:.1f}mm" if total_rain > 0 else " 강수 없음"
        weather_desc = f"최고 {temp_range}{rain_str}"
    else:
        weather_desc = "날씨 조회 불가"

    weather_full = "\n".join(daily_lines)
    return weather_score, weather_desc, weather_full


def _score_flight(
    flight: FlightPrice,
    flights: list[FlightPrice],
    weather_score: float,
    prefer_nonstop: bool,
) -> tuple[float, str]:
    max_price = max(f.price for f in flights)
    min_price = min(f.price for f in flights)
    price_range = max_price - min_price
    # 결과가 1개이면 price_range=0 → 중간값(2.5점) 부여
    if price_range == 0:
        price_score = 2.5
    else:
        price_score = round((max_price - flight.price) / price_range * 5, 2)

    stops_factor = 4.0 if prefer_nonstop else 2.0
    stops_penalty = flight.stops * stops_factor

    tc = (flight.time_category or "").upper()
    time_penalty = _TIME_PENALTY.get(tc, 0.0)

    total = price_score + weather_score - stops_penalty + time_penalty

    time_label = _TIME_LABEL.get(tc, "시간미정")
    stops_label = "직항" if flight.stops == 0 else f"경유 {flight.stops}회"
    reason = f"항공 {flight.price:,}원 · {stops_label} · {time_label}"
    return round(total, 2), reason


def _display_top10(candidates: list[dict], dest: str, trip_nights: int) -> None:
    print(f"\n{'─'*90}")
    print(f"  🗓️  {dest} 왕복 항공권 추천 TOP {len(candidates)} ({trip_nights}박 기준, 가격은 왕복 기준)")
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
        star = "★★★" if i == 1 else ("★★" if i <= 3 else "★")
        return_date = c.get("check_out", "")
        # MM/DD 형식으로 짧게 표시
        ret_short = return_date[5:] if return_date else "?"
        print(
            f"  {i:>2}  {c['check_in']:^10}  {ret_short:^10}  {time_str:^13}  {airline:<12}  "
            f"{price_str:>11}  {stops_label:^6}  {star}"
        )
        print(f"      날씨: {weather_short}")
    print(f"{'─'*90}")


def _prompt_selection(candidates: list[dict]) -> int:
    while True:
        try:
            raw = input(f"\n  번호를 선택하세요 (1-{len(candidates)}, Enter = 1번): ").strip()
            if not raw:
                return 0
            idx = int(raw) - 1
            if 0 <= idx < len(candidates):
                return idx
            print(f"  ⚠ 1~{len(candidates)} 사이 숫자를 입력하세요.")
        except (ValueError, EOFError):
            return 0


def make_date_optimizer_node(interactive: bool = True):
    """date_optimizer_node 팩토리.

    Args:
        interactive: True면 TOP 10 표시 후 사용자 확인, False면 1위 자동 선택 (API 모드)
    """
    def date_optimizer_node(state: AgentState) -> dict:
        intent = state["intent"]
        dest = intent["destination"]
        trip_nights = intent["trip_nights"]
        prefer_nonstop: bool = intent.get("prefer_nonstop", False)
        today = datetime.now().date()

        print(f"\n🗓️  [날짜 최적화] {dest} 항공권 + 날씨 교차 분석 중...")
        if prefer_nonstop:
            print("  → 직항 선호 모드: 경유 감점 2배 적용")

        iata_dest = get_iata(dest)
        if not iata_dest:
            print(f"  ✗ IATA 코드 없음: '{dest}' — 날씨 기반 추천으로 전환")
            return _weather_only_candidates(dest, trip_nights, today, intent)

        iata_origin = "ICN"
        domestic = iata_is_domestic(iata_dest)
        print(f"  → {iata_origin} → {iata_dest} ({'국내선' if domestic else '국제선'}), {trip_nights}박 기준")

        if domestic:
            print("  ✗ 국내선 — 항공권 조회 불가, 날씨 기반 추천으로 전환")
            return _weather_only_candidates(dest, trip_nights, today, intent)

        target_months: list = intent.get("target_months") or []
        if not target_months:
            for i in range(1, 4):
                m = (today.replace(day=1) + timedelta(days=32 * i)).replace(day=1)
                target_months.append(m.strftime("%Y%m"))

        flights = get_cheapest_dates(
            origin=iata_origin,
            destination=iata_dest,
            months=target_months,
            trip_days=[trip_nights + 1],
            top_n=50,
        )

        if not flights:
            print("  ✗ 항공권 조회 실패 — 날씨 기반 추천으로 전환")
            return _weather_only_candidates(dest, trip_nights, today, intent)
        print(f"  ✓ 항공권 {len(flights)}건 조회 완료")

        # 1단계: 가격 + 경유 + 시간대만으로 빠른 사전 점수 계산 (API 호출 없음)
        print(f"  → 사전 점수 계산 후 상위 20건 날씨 조회...")
        pre_scored = []
        for flight in flights:
            pre_score, _ = _score_flight(flight, flights, weather_score=0.0, prefer_nonstop=prefer_nonstop)
            check_out = (
                datetime.strptime(flight.date, "%Y-%m-%d").date() + timedelta(days=trip_nights)
            ).isoformat()
            pre_scored.append((pre_score, flight, check_out))
        pre_scored.sort(key=lambda x: x[0], reverse=True)
        top20_flights = pre_scored[:20]

        # 2단계: 상위 20건에 전체 여행 기간 날씨 조회 후 최종 종합 점수
        candidates = []
        for _, flight, check_out in top20_flights:
            weather_score, weather_desc, weather_full = _get_trip_weather(
                dest, flight.date, check_out
            )
            total_score, reason = _score_flight(flight, flights, weather_score, prefer_nonstop)

            candidates.append({
                "check_in": flight.date,
                "check_out": check_out,
                "flight_price": flight.price,
                "weather_summary": weather_desc,       # 표 출력용 요약
                "weather_full": weather_full,          # weather_node 재사용용 전체 텍스트
                "score": total_score,
                "reason": reason,
                "stops": flight.stops,
                "time_category": flight.time_category,
                "airline_codes": flight.airline_codes,
                "airline_name": _airline_label(flight.airline_codes),
                "departure_time": getattr(flight, "departure_time", ""),
                "arrival_time": getattr(flight, "arrival_time", ""),
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        top10 = candidates[:10]

        _display_top10(top10, dest, trip_nights)

        if interactive:
            selected_idx = _prompt_selection(top10)
        else:
            selected_idx = 0

        selected = top10[selected_idx]

        # 선택된 1건만 SerpAPI로 출발/도착 시각 enrichment (이미 있으면 스킵)
        if not selected.get("departure_time"):
            _enrich_with_serpapi_times([selected], iata_origin, iata_dest)

        dep = selected.get("departure_time", "")
        arr = selected.get("arrival_time", "")
        time_str = f" ({dep.split()[-1]} → {arr.split()[-1]})" if dep and arr else ""
        print(f"\n  ✓ 선택된 날짜: {selected['check_in']} ~ {selected['check_out']} | {selected['reason']}{time_str}")

        updated_intent = dict(intent)
        updated_intent["check_in"] = selected["check_in"]
        updated_intent["check_out"] = selected["check_out"]

        # weather_node가 재호출하지 않도록 날씨 데이터를 미리 채워 넘긴다
        full_weather = selected.get("weather_full", "")
        # "강우 Xmm" 패턴만 체크 (강수확률 문자열 오탐 방지)
        import re as _re
        is_rainy = any(
            _re.search(r"강우 ([0-9.]+)mm", line) and float(_re.search(r"강우 ([0-9.]+)mm", line).group(1)) > 1.0
            for line in full_weather.splitlines()
            if line
        )

        return {
            "candidate_dates": top10[:3],
            "intent": updated_intent,
            "date_fixed": True,
            "weather_summary": full_weather,
            "is_rainy": is_rainy,
        }

    return date_optimizer_node
