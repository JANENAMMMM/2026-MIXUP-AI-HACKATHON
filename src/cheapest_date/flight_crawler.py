# -*- coding: utf-8 -*-
"""SerpAPI Google Flights를 통해 후보 날짜별 항공권 최저가를 조회한다."""

import os
from datetime import datetime, timedelta

import requests

from .models import FlightPrice

_SERPAPI_URL = "https://serpapi.com/search.json"


def get_cheapest_dates(
    origin: str,
    destination: str,
    candidate_dates: list[str],
    trip_nights: int,
    is_domestic: bool = False,
    top_n: int = 10,
    api_key: str | None = None,
) -> list[FlightPrice]:
    """SerpAPI Google Flights로 후보 날짜별 왕복 최저가를 조회한다.

    Args:
        origin:          출발 공항 IATA 코드 (예: 'ICN')
        destination:     도착 공항 IATA 코드 (예: 'LHR')
        candidate_dates: 조회할 출발 날짜 목록 (YYYY-MM-DD)
        trip_nights:     숙박 일수 (귀국일 = 출발일 + trip_nights)
        is_domestic:     국내선 여부 (SerpAPI google_flights 국내선 미지원 → 빈 리스트)
        top_n:           반환할 최대 결과 수
        api_key:         SerpAPI 키 (없으면 환경변수 SERPAPI_KEY 사용)

    Returns:
        가격 오름차순 FlightPrice 리스트. 키 없거나 국내선이면 빈 리스트.
    """
    if is_domestic:
        return []

    key = api_key or os.getenv("SERPAPI_KEY")
    if not key:
        return []

    results = []
    for outbound in candidate_dates:
        return_date = (
            datetime.strptime(outbound, "%Y-%m-%d") + timedelta(days=trip_nights)
        ).strftime("%Y-%m-%d")

        price = _fetch_price(origin, destination, outbound, return_date, key)
        if price:
            results.append(FlightPrice(
                date=outbound,
                return_date=return_date,
                price=price,
                trip_days=trip_nights + 1,
            ))

    results.sort(key=lambda f: f.price)
    return results[:top_n]


def _fetch_price(
    origin: str,
    destination: str,
    outbound_date: str,
    return_date: str,
    api_key: str,
) -> int | None:
    """SerpAPI google_flights로 특정 날짜 왕복 최저가를 반환한다."""
    params = {
        "engine": "google_flights",
        "departure_id": origin,
        "arrival_id": destination,
        "outbound_date": outbound_date,
        "return_date": return_date,
        "currency": "KRW",
        "hl": "en",
        "api_key": api_key,
    }
    try:
        resp = requests.get(_SERPAPI_URL, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        lowest = data.get("price_insights", {}).get("lowest_price")
        if lowest:
            return int(lowest)

        for key_name in ("best_flights", "other_flights"):
            flights = data.get(key_name, [])
            if flights and flights[0].get("price"):
                return int(flights[0]["price"])
    except Exception as e:
        print(f"    ✗ {outbound_date}: {e}")
    return None
