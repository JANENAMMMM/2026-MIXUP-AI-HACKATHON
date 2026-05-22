import os
import requests

from .models import Place


def search_places(query: str) -> list[Place]:
    """Google Places API로 장소를 검색한다.

    Args:
        query: 검색어 (예: "Tokyo Shibuya restaurants", "서울 카페")

    Returns:
        list[Place] - 이름과 주소가 담긴 장소 목록
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY 환경변수가 설정되지 않았습니다.")

    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress",
    }

    response = requests.post(url, headers=headers, json={"textQuery": query}, timeout=30)
    response.raise_for_status()
    return [Place.from_api_response(p) for p in response.json().get("places", [])]
