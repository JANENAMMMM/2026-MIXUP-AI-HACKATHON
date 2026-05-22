# -*- coding: utf-8 -*-
"""네이버 항공권 GraphQL API (primary) + SerpAPI Google Flights (fallback)로 날짜별 최저가를 조회한다."""

import os
from datetime import datetime, timedelta, date as date_cls

import requests

from .models import FlightPrice
from .iata import AIRPORT_TO_NAVER

_NAVER_URL = "https://flight-api.naver.com/graphql"
_SERPAPI_URL = "https://serpapi.com/search.json"

_QUERY = (
    "query GET_RECOMMEND_BY_CITY("
    "$departureLocationCode: String, $departureLocationType: String, "
    "$arrivalLocationCode: String, $arrivalLocationType: String, "
    "$continentIds: [Int!], $countryCodes: [String!], "
    "$departureDate: String, $returnDate: String, "
    "$departureMonths: [String!], $duration: [Int!], "
    "$isDomestic: Boolean, $isMappable: Boolean, $isNonstop: Boolean, "
    "$price: [Int!], $timeCategories: [DepartureTimeCategory!], "
    "$themeIds: [Int!], $tripDays: [Int!], $tripType: String"
    ") {\n"
    "  minPricesByDate(\n"
    "    departureLocationCode: $departureLocationCode\n"
    "    departureLocationType: $departureLocationType\n"
    "    arrivalLocationCode: $arrivalLocationCode\n"
    "    arrivalLocationType: $arrivalLocationType\n"
    "    continentIds: $continentIds\n"
    "    countryCodes: $countryCodes\n"
    "    departureDate: $departureDate\n"
    "    returnDate: $returnDate\n"
    "    departureMonths: $departureMonths\n"
    "    duration: $duration\n"
    "    isDomestic: $isDomestic\n"
    "    isMappable: $isMappable\n"
    "    isNonstop: $isNonstop\n"
    "    price: $price\n"
    "    themeIds: $themeIds\n"
    "    timeCategories: $timeCategories\n"
    "    tripDays: $tripDays\n"
    "    tripType: $tripType\n"
    "  ) {\n"
    "    departureLocation { iataCode cityName popularity __typename }\n"
    "    arrivalLocation { iataCode cityName popularity __typename }\n"
    "    departureDate\n"
    "    airlineCodes\n"
    "    duration\n"
    "    isDomestic\n"
    "    minPrice\n"
    "    returnDate\n"
    "    stops\n"
    "    timeCategory\n"
    "    tripDays\n"
    "    tripType\n"
    "    __typename\n"
    "  }\n"
    "}"
)


def _build_naver_headers() -> dict:
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "ko-KR,ko;q=0.9",
        "content-type": "application/json",
        "origin": "https://flight.naver.com",
        "referer": "https://flight.naver.com/",
        "user-agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/136.0.0.0 Safari/537.36"
        ),
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
    }
    cookie = os.getenv("NAVER_FLIGHT_COOKIE")
    if cookie:
        headers["cookie"] = cookie
    return headers


def _to_iso(date_str: str) -> str:
    """'20260525' → '2026-05-25'"""
    return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"


def _naver_cheapest_dates(
    origin: str,
    destination: str,
    months: list[str],
    is_nonstop: bool = False,
    top_n: int = 50,
    origin_type: str = "airport",
    destination_type: str = "airport",
) -> list[FlightPrice]:
    """네이버 GraphQL minPricesByDate로 전체 월 날짜별 최저가를 단건 호출로 조회한다."""
    payload = {
        "operationName": "GET_RECOMMEND_BY_CITY",
        "variables": {
            "departureLocationCode": origin,
            "departureLocationType": origin_type,
            "arrivalLocationCode": destination,
            "arrivalLocationType": destination_type,
            "departureMonths": months,
            "isDomestic": False,
            "isNonstop": is_nonstop,
            "tripType": "RT",
        },
        "query": _QUERY,
    }
    try:
        res = requests.post(_NAVER_URL, headers=_build_naver_headers(), json=payload, timeout=10)
        res.raise_for_status()
    except requests.RequestException as e:
        print(f"  [flight] 네이버 요청 실패: {e}")
        return []

    raw = res.json().get("data", {}).get("minPricesByDate") or []
    # tripDays 필터 없이 전체 수집 — date_optimizer가 check_out을 자체 계산하므로 불필요
    results = [
        FlightPrice(
            date=_to_iso(item["departureDate"]),
            return_date=_to_iso(item["returnDate"]),
            price=item["minPrice"],
            stops=item.get("stops", 0),
            duration=item.get("duration", 0),
            airline_codes=item.get("airlineCodes", []),
            trip_days=item.get("tripDays", 0),
            time_category=item.get("timeCategory", ""),
        )
        for item in raw
        if item.get("minPrice")
    ]
    results.sort(key=lambda f: f.price)
    return results[:top_n]


def _serpapi_fetch_flight(
    origin: str,
    destination: str,
    outbound_date: str,
    return_date: str,
    api_key: str,
) -> dict | None:
    """SerpAPI로 단일 날짜 항공편을 조회하고 price/airline/times를 반환한다."""
    params = {
        "engine": "google_flights",
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": outbound_date,
        "return_date": return_date,
        "currency": "KRW",
        "hl": "ko",
        "api_key": api_key,
    }
    try:
        resp = requests.get(_SERPAPI_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        for key_name in ("best_flights", "other_flights"):
            flights = data.get(key_name, [])
            if not flights:
                continue
            f = flights[0]
            price = f.get("price")
            if not price:
                continue

            # 첫 번째 leg에서 출발/도착 시간과 항공사 추출
            legs = f.get("flights", [])
            dep_time = arr_time = ""
            airline_codes: list[str] = []
            if legs:
                first_leg = legs[0]
                dep_time = first_leg.get("departure_airport", {}).get("time", "")
                last_leg = legs[-1]
                arr_time = last_leg.get("arrival_airport", {}).get("time", "")
                for leg in legs:
                    iata = leg.get("airline", "")
                    if iata and iata not in airline_codes:
                        airline_codes.append(iata)

            return {
                "price": int(price),
                "airline_codes": airline_codes,
                "departure_time": dep_time,
                "arrival_time": arr_time,
            }

        # price_insights만 있는 경우 (시간 정보 없음)
        lowest = data.get("price_insights", {}).get("lowest_price")
        if lowest:
            return {"price": int(lowest), "airline_codes": [], "departure_time": "", "arrival_time": ""}

    except Exception as e:
        print(f"    ✗ {outbound_date}: {e}")
    return None


def _serpapi_cheapest_dates(
    origin: str,
    destination: str,
    months: list[str],
    trip_nights: int,
    top_n: int = 10,
    api_key: str | None = None,
) -> list[FlightPrice]:
    """SerpAPI google_flights로 months에서 생성한 후보 날짜별 왕복 최저가를 조회한다. (fallback)"""
    key = api_key or os.getenv("SERPAPI_KEY")
    if not key:
        return []

    today = date_cls.today()
    candidate_dates: list[str] = []
    for month_str in months:
        year, month = int(month_str[:4]), int(month_str[4:])
        d = date_cls(year, month, 1)
        while d.month == month and len(candidate_dates) < 8:
            if (d - today).days > 7:
                candidate_dates.append(d.isoformat())
            d += timedelta(days=4)

    if not candidate_dates:
        return []

    results = []
    for outbound in candidate_dates:
        return_date = (
            datetime.strptime(outbound, "%Y-%m-%d") + timedelta(days=trip_nights)
        ).strftime("%Y-%m-%d")
        info = _serpapi_fetch_flight(origin, destination, outbound, return_date, key)
        if info and info["price"]:
            results.append(FlightPrice(
                date=outbound,
                return_date=return_date,
                price=info["price"],
                trip_days=trip_nights + 1,
                airline_codes=info["airline_codes"],
                departure_time=info["departure_time"],
                arrival_time=info["arrival_time"],
            ))

    results.sort(key=lambda f: f.price)
    return results[:top_n]


def get_cheapest_dates(
    origin: str,
    destination: str,
    months: list[str],
    trip_days: list[int],
    is_nonstop: bool = False,
    top_n: int = 50,
    origin_type: str = "airport",
    destination_type: str = "airport",
) -> list[FlightPrice]:
    """네이버 항공권 API (primary) → SerpAPI (fallback)로 날짜별 최저가를 조회한다.

    Args:
        origin:      출발 공항 IATA 코드 (예: 'ICN')
        destination: 도착 공항 IATA 코드 (예: 'LHR')
        months:      조회 월 목록 (예: ['202607'])
        trip_days:   여행 일수 목록 (참고용, tripDays 필터 없이 전체 반환)
        is_nonstop:  직항만 조회 여부
        top_n:       최대 반환 수

    Returns:
        가격 오름차순 FlightPrice 리스트.
    """
    # 네이버는 일부 도시(오사카·도쿄 등)에 공항 코드 대신 도시 코드를 써야 함
    naver_dest, naver_dest_type = AIRPORT_TO_NAVER.get(destination, (destination, destination_type))
    naver_orig, naver_orig_type = AIRPORT_TO_NAVER.get(origin, (origin, origin_type))

    print(f"  → 네이버 항공권 API 조회 중 (월: {months})...")
    results = _naver_cheapest_dates(
        naver_orig, naver_dest, months, is_nonstop, top_n, naver_orig_type, naver_dest_type
    )

    _NAVER_MIN = 5  # 이 미만이면 SerpAPI로 보충
    trip_nights = max(trip_days) - 1 if trip_days else 4

    if len(results) >= _NAVER_MIN:
        print(f"  ✓ 네이버 API: {len(results)}개 날짜, 최저 {results[0].price:,}원 ({results[0].date})")
        return results

    if results:
        print(f"  △ 네이버 API: {len(results)}건 (부족) → SerpAPI 보충 조회...")
    else:
        print("  ✗ 네이버 API 빈 응답 → SerpAPI fallback 시도...")

    serpapi_results = _serpapi_cheapest_dates(origin, destination, months, trip_nights, min(top_n, 10))

    if serpapi_results:
        # Naver + SerpAPI 합산, 중복 날짜는 더 싼 것만 유지
        combined: dict[str, FlightPrice] = {f.date: f for f in serpapi_results}
        for f in results:
            if f.date not in combined or f.price < combined[f.date].price:
                combined[f.date] = f
        merged = sorted(combined.values(), key=lambda f: f.price)
        print(f"  ✓ 합산 결과: {len(merged)}개 날짜, 최저 {merged[0].price:,}원 ({merged[0].date})")
        return merged[:top_n]

    if results:
        print(f"  △ SerpAPI도 실패, 네이버 {len(results)}건만 사용")
        print(f"  ✓ 네이버 API: {len(results)}개 날짜, 최저 {results[0].price:,}원 ({results[0].date})")
        return results

    print("  ✗ 모든 API 실패")
    return []
