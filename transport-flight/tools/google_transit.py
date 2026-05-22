import os
import requests
from typing import Optional, Literal

SERPAPI_BASE = "https://serpapi.com/search"

# prefer 파라미터 — travel_mode=3(대중교통)일 때만 유효
TransitPrefer = Literal["bus", "subway", "train", "tram_light_rail"]


def _parse_route(item: dict) -> dict:
    """directions 배열의 경로 하나를 파싱합니다."""
    trips = []
    for trip in item.get("trips", []):
        start_stop = trip.get("start_stop", {})
        end_stop = trip.get("end_stop", {})
        service = trip.get("service_run_by", {})

        trips.append({
            "mode": trip.get("travel_mode", ""),
            "title": trip.get("title", ""),
            "start_stop": {
                "name": start_stop.get("name", ""),
                "time": start_stop.get("time", ""),
            },
            "end_stop": {
                "name": end_stop.get("name", ""),
                "time": end_stop.get("time", ""),
            },
            "stops_count": len(trip.get("stops", [])),
            "service": service.get("name", ""),
            "duration_minutes": trip.get("duration", 0) // 60,
        })

    # via 필드가 없으면 첫 번째 Transit trip 제목으로 대체
    transit_trips = [t for t in trips if t["mode"].lower() == "transit"]
    summary = item.get("via") or (transit_trips[0]["title"] if transit_trips else "")

    return {
        "summary": summary,
        "duration_minutes": item.get("duration", 0) // 60,
        "formatted_duration": item.get("formatted_duration", ""),
        "distance": item.get("formatted_distance", ""),
        "start_time": item.get("start_time", ""),
        "end_time": item.get("end_time", ""),
        "cost": item.get("cost"),
        "currency": item.get("currency", ""),
        "trips": trips,
    }


def search_transit(
    start_addr: str,
    end_addr: str,
    depart_time: Optional[str] = None,
    prefer: Optional[TransitPrefer] = None,
    max_results: int = 3,
) -> dict:
    """
    Google Maps Directions API로 대중교통 경로를 검색합니다.

    Args:
        start_addr:  출발지 주소 또는 지명 (예: "서울역", "Seoul Station")
        end_addr:    도착지 주소 또는 지명 (예: "부산역", "Busan Station")
        depart_time: 출발 시각 "YYYY-MM-DD HH:MM". None이면 현재 시각 기준.
        prefer:      선호 교통수단 — "bus" | "subway" | "train" | "tram_light_rail"
        max_results: 반환할 최대 경로 수

    Returns:
        {
            "start": str,
            "end": str,
            "routes": [
                {
                    "summary": str,              # 경유 노선 요약 (예: "KTX via 대전")
                    "duration_minutes": int,
                    "formatted_duration": str,   # 예: "2시간 40분"
                    "distance": str,             # 예: "325 km"
                    "start_time": str,
                    "end_time": str,
                    "cost": int | None,
                    "currency": str,
                    "trips": [
                        {
                            "mode": str,         # TRANSIT, WALKING 등
                            "title": str,        # 노선명 (예: "KTX 101")
                            "start_stop": {"name": str, "time": str},
                            "end_stop":   {"name": str, "time": str},
                            "stops_count": int,
                            "service": str,      # 운영사 (예: "코레일")
                            "duration_minutes": int
                        }
                    ]
                }
            ],
            "error": str  # 경로 없을 때만
        }
    """
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        raise EnvironmentError("SERPAPI_KEY 환경변수가 설정되지 않았습니다.")

    params: dict = {
        "engine": "google_maps_directions",
        "start_addr": start_addr,
        "end_addr": end_addr,
        "travel_mode": 3,   # 대중교통
        "distance_unit": 0, # km
        "hl": "ko",
        "gl": "kr",
        "api_key": api_key,
    }

    if prefer:
        params["prefer"] = prefer
    if depart_time:
        params["time"] = "depart_at"
        params["depart_time"] = depart_time

    response = requests.get(SERPAPI_BASE, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    raw = data.get("directions", [])
    routes = [_parse_route(item) for item in raw[:max_results]]

    result: dict = {
        "start": start_addr,
        "end": end_addr,
        "routes": routes,
    }

    if not routes:
        result["error"] = f"{start_addr} → {end_addr} 대중교통 경로를 찾을 수 없습니다."

    return result
