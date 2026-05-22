import os
import requests
from typing import Optional, Literal

from .models import Route, TransitSearchResult

SERPAPI_BASE = "https://serpapi.com/search"

TransitPrefer = Literal["bus", "subway", "train", "tram_light_rail"]


def search_transit(
    start_addr: str,
    end_addr: str,
    depart_time: Optional[str] = None,
    prefer: Optional[TransitPrefer] = None,
    max_results: int = 3,
) -> TransitSearchResult:
    """Google Maps Directions API로 대중교통 경로를 검색한다.

    Args:
        start_addr:  출발지 주소 또는 지명 (예: "서울역", "Seoul Station")
        end_addr:    도착지 주소 또는 지명 (예: "부산역")
        depart_time: 출발 시각 "YYYY-MM-DD HH:MM". None이면 현재 시각 기준.
        prefer:      선호 교통수단 — "bus" | "subway" | "train" | "tram_light_rail"
        max_results: 반환할 최대 경로 수

    Returns:
        TransitSearchResult - 경로 목록과 검색 메타 정보
    """
    api_key = os.environ.get("SERPAPI_KEY")
    if not api_key:
        raise EnvironmentError("SERPAPI_KEY 환경변수가 설정되지 않았습니다.")

    params: dict = {
        "engine": "google_maps_directions",
        "start_addr": start_addr,
        "end_addr": end_addr,
        "travel_mode": 3,
        "distance_unit": 0,
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

    routes = [Route.from_api_response(item) for item in data.get("directions", [])[:max_results]]

    result = TransitSearchResult(start=start_addr, end=end_addr, routes=routes)
    if not routes:
        result.error = f"{start_addr} → {end_addr} 대중교통 경로를 찾을 수 없습니다."
    return result
