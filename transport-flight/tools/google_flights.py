import os
import requests
from typing import Optional

SERPAPI_BASE = "https://serpapi.com/search"


def _parse_flight_group(item: dict, adults: int, booking_url: str) -> dict:
    legs = item.get("flights", [])
    if not legs:
        return {}

    first_leg = legs[0]
    last_leg = legs[-1]

    layovers = [
        {
            "airport": lv.get("name", ""),
            "airport_code": lv.get("id", ""),
            "duration_minutes": lv.get("duration", 0),
            "overnight": lv.get("overnight", False),
        }
        for lv in item.get("layovers", [])
    ]

    price_per_person = item.get("price", 0)

    return {
        "airline": first_leg.get("airline", ""),
        "flight_number": first_leg.get("flight_number", ""),
        "departure_time": first_leg.get("departure_airport", {}).get("time", ""),
        "arrival_time": last_leg.get("arrival_airport", {}).get("time", ""),
        "duration_minutes": item.get("total_duration", 0),
        "stops": len(legs) - 1,
        "layovers": layovers,
        "price_per_person": price_per_person,
        "total_price": price_per_person * adults,
        "booking_url": booking_url,
    }


def search_flights(
    departure_id: str,
    arrival_id: str,
    outbound_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    currency: str = "KRW",
    max_results: int = 3,
) -> dict:
    """
    Google Flights 항공편 검색.

    Args:
        departure_id:  출발 공항 IATA 코드 (예: ICN, JFK, NRT)
        arrival_id:    도착 공항 IATA 코드 (예: CDG, LHR, PUS)
        outbound_date: 출발 날짜 YYYY-MM-DD
        return_date:   귀환 날짜 YYYY-MM-DD. 있으면 왕복(price = 왕복 합산가), 없으면 편도.
        adults:        성인 탑승객 수
        currency:      통화 코드 (기본 KRW)
        max_results:   반환할 최대 항공편 수

    Returns:
        {
            "departure": str,
            "arrival": str,
            "outbound_date": str,
            "return_date": str | None,
            "adults": int,
            "currency": str,
            "flights": [
                {
                    "airline": str,
                    "flight_number": str,
                    "departure_time": str,
                    "arrival_time": str,
                    "duration_minutes": int,
                    "stops": int,
                    "layovers": [{"airport", "airport_code", "duration_minutes", "overnight"}],
                    "price_per_person": int,
                    "total_price": int,
                    "booking_url": str
                }
            ],
            "error": str  # 항공편 없을 때만
        }
    """
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        raise EnvironmentError("SERPAPI_KEY 환경변수가 설정되지 않았습니다.")

    params: dict = {
        "engine": "google_flights",
        "departure_id": departure_id,
        "arrival_id": arrival_id,
        "outbound_date": outbound_date,
        "adults": adults,
        "currency": currency,
        "hl": "ko",
        "gl": "kr",
        "api_key": api_key,
        "type": "1" if return_date else "2",
    }
    if return_date:
        params["return_date"] = return_date

    response = requests.get(SERPAPI_BASE, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    booking_url = data.get("search_metadata", {}).get("google_flights_url", "")
    raw = data.get("best_flights", []) + data.get("other_flights", [])
    flights = [
        parsed
        for item in raw[:max_results]
        if (parsed := _parse_flight_group(item, adults, booking_url))
    ]

    result: dict = {
        "departure": departure_id,
        "arrival": arrival_id,
        "outbound_date": outbound_date,
        "return_date": return_date,
        "adults": adults,
        "currency": currency,
        "flights": flights,
    }

    if not flights:
        result["error"] = f"{departure_id} → {arrival_id} 구간 항공편을 찾을 수 없습니다."

    return result
