# -*- coding: utf-8 -*-
"""네이버 항공권 GraphQL API를 통해 날짜별 최저가를 조회한다."""

import os

import requests
from dotenv import load_dotenv

from .models import FlightPrice

load_dotenv()

_URL = "https://flight-api.naver.com/graphql"


def _build_headers() -> dict:
    headers = {
        "accept": "application/json, text/plain, */*",
        "accept-language": "ko-KR,ko;q=0.9",
        "content-type": "application/json",
        "origin": "https://flight.naver.com",
        "referer": "https://flight.naver.com/",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
    }
    cookie = os.getenv("NAVER_FLIGHT_COOKIE")
    if cookie:
        headers["cookie"] = cookie
    return headers

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


def _to_iso(date_str: str) -> str:
    """'20260525' → '2026-05-25'"""
    return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"


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
    """네이버 항공권 추천 일정 API로 날짜별 최저가를 조회한다.

    Args:
        origin:           출발 공항 IATA 코드 (예: 'ICN')
        destination:      도착 공항 IATA 코드 (예: 'LHR')
        months:           조회 월 목록 (예: ['202606', '202607', '202608', '202609'])
        trip_days:        여행 일수 목록 1~15 (예: [4] → 3박4일)
        is_nonstop:       True면 직항만 조회
        top_n:            반환할 최저가 결과 수 (클라이언트 필터 후)
        origin_type:      출발지 타입 ('airport' | 'city')
        destination_type: 도착지 타입 ('airport' | 'city')

    Returns:
        trip_days에 해당하는 결과를 minPrice 오름차순 상위 top_n개로 반환.
        요청 실패 시 빈 리스트 반환.

    Note:
        tripDays는 서버에서 무시되므로 variables에서 제외하고 클라이언트에서 필터링한다.
    """
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
        res = requests.post(_URL, headers=_build_headers(), json=payload, timeout=10)
        res.raise_for_status()
    except requests.RequestException as e:
        print(f"[flight_crawler] 요청 실패: {e}")
        return []

    raw = res.json().get("data", {}).get("minPricesByDate") or []

    results = [
        FlightPrice(
            date=_to_iso(item["departureDate"]),
            return_date=_to_iso(item["returnDate"]),
            price=item["minPrice"],
            stops=item.get("stops", 0),
            duration=item.get("duration", 0),
            airline_codes=item.get("airlineCodes", []),
            trip_days=item.get("tripDays", 0),
        )
        for item in raw
        if item.get("minPrice") and item.get("tripDays") in trip_days
    ]

    results.sort(key=lambda f: f.price)
    return results[:top_n]
