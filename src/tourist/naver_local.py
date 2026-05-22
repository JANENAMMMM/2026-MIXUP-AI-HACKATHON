import os
import requests

from .models import LocalPlace


def search_local(query: str, display: int = 5) -> list[LocalPlace]:
    """네이버 지역 검색 API로 장소를 검색한다.

    Args:
        query: 검색어 (예: "해운대 횟집", "강남 카페")
        display: 반환할 결과 수 (기본 5, 최대 5)

    Returns:
        list[LocalPlace] - 이름/주소/전화번호 등이 담긴 장소 목록
    """
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise EnvironmentError("NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET 환경변수가 설정되지 않았습니다.")

    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }

    response = requests.get(url, headers=headers, params={"query": query, "display": display}, timeout=30)
    response.raise_for_status()
    return [LocalPlace.from_api_response(item) for item in response.json().get("items", [])]
