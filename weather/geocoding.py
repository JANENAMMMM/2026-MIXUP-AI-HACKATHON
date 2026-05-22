# -*- coding: utf-8 -*-
"""도시명 → 위경도 변환 (Nominatim / OpenStreetMap)"""

import requests
from .config import NOMINATIM_URL, NOMINATIM_HEADERS


def get_coordinates(city_name: str) -> tuple[float, float, str, str, str]:
    """도시명을 위경도 좌표로 변환한다.

    Args:
        city_name: 도시명 (한글/영문 모두 가능. 예: '서울', 'Tokyo', 'New York')

    Returns:
        (위도, 경도, 도시명, 국가명, 타임존)

    Raises:
        ValueError: 도시를 찾을 수 없는 경우
        requests.HTTPError: API 호출 실패
    """
    resp = requests.get(
        NOMINATIM_URL,
        params={"q": city_name, "format": "json", "limit": 1, "addressdetails": 1},
        headers=NOMINATIM_HEADERS,
    )
    resp.raise_for_status()

    data = resp.json()
    if not data:
        raise ValueError(
            f"'{city_name}' 위치를 찾을 수 없습니다. 다른 표기로 시도해보세요.\n"
            f"예) '서울' → 'Seoul', '뉴욕' → 'New York'"
        )

    r = data[0]
    addr = r.get("address", {})

    # 도시 단위 이름 우선순위: city > town > county > display_name 첫 번째 토큰
    name = (
        addr.get("city")
        or addr.get("town")
        or addr.get("county")
        or r["display_name"].split(",")[0]
    )
    country = addr.get("country", "")

    # 타임존은 Open-Meteo가 좌표로 자동 결정
    return float(r["lat"]), float(r["lon"]), name, country, "auto"
