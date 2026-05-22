import urllib.parse
from dataclasses import dataclass, field


@dataclass
class HotelSearchRequest:
    """호텔 검색 요청 파라미터."""
    q: str                              # 검색어 (예: "Seoul hotels")
    check_in_date: str                  # 체크인 날짜 (YYYY-MM-DD)
    check_out_date: str                 # 체크아웃 날짜 (YYYY-MM-DD)
    adults: int = 2
    children: int = 0
    children_ages: str | None = None    # 어린이 나이 (쉼표 구분, 예: "4,8")
    gl: str = "kr"
    hl: str = "ko"
    currency: str = "KRW"
    sort_by: int | None = None          # 3=가격순
    min_price: int | None = None
    max_price: int | None = None
    rating: int | None = None           # 최소 평점 (1~10)
    hotel_class: str | None = None      # 호텔 등급 (예: "3,4,5")
    free_cancellation: bool | None = None
    special_offers: bool | None = None
    eco_certified: bool | None = None
    vacation_rentals: bool | None = None
    bedrooms: int | None = None
    bathrooms: int | None = None
    next_page_token: str | None = None
    no_cache: bool = False


@dataclass
class Hotel:
    """개별 호텔 정보."""
    name: str
    address: str | None = None
    description: str | None = None
    thumbnail: str | None = None
    type: str | None = None
    hotel_class: str | None = None
    overall_rating: float | None = None
    reviews: int | None = None
    rate_per_night: str | None = None   # 1박 최저 요금
    total_rate: str | None = None       # 체류 전체 요금
    amenities: list[str] = field(default_factory=list)
    property_token: str | None = None
    details_link: str | None = None

    @classmethod
    def from_api_response(cls, data: dict) -> "Hotel":
        # Robust thumbnail extraction
        thumbnail = data.get("thumbnail")
        if not thumbnail:
            # Try images[0].thumbnail or images[0].src or images[0].image
            images = data.get("images") or data.get("photos")
            if isinstance(images, list) and images:
                img0 = images[0]
                thumb = img0.get("thumbnail") or img0.get("src") or img0.get("image")
                if thumb:
                    thumbnail = thumb
        elif isinstance(thumbnail, dict):
            thumbnail = thumbnail.get("image") or thumbnail.get("src") or thumbnail.get("source")

        address = data.get("address") or data.get("address_snippet") or data.get("location") or ""
        name = data.get("name", "")

        # 사용자가 바로 접속할 수 있도록 모든 호텔의 상세 링크를 구글 트래블 검색 URL로 일괄 통일합니다.
        search_query = f"{name} {address}".strip()
        details_link = f"https://www.google.com/travel/search?q={urllib.parse.quote(search_query)}"

        return cls(
            name=name,
            address=address,
            description=data.get("description") or data.get("snippet") or data.get("description_snippet"),
            thumbnail=thumbnail,
            type=data.get("type"),
            hotel_class=data.get("hotel_class") or data.get("extracted_hotel_class"),
            overall_rating=data.get("overall_rating"),
            reviews=data.get("reviews"),
            rate_per_night=(data.get("rate_per_night", {}) or {}).get("lowest"),
            total_rate=(data.get("total_rate", {}) or {}).get("lowest"),
            amenities=data.get("amenities", []),
            property_token=data.get("property_token"),
            details_link=details_link,
        )


@dataclass
class HotelSearchResult:
    """호텔 검색 결과."""
    query: str
    check_in_date: str
    check_out_date: str
    adults: int
    total_results: int | None = None
    hotels: list[Hotel] = field(default_factory=list)

    @classmethod
    def from_api_response(cls, data: dict, request: HotelSearchRequest) -> "HotelSearchResult":
        params = data.get("search_parameters", {})
        info = data.get("search_information", {})
        return cls(
            query=params.get("q", request.q),
            check_in_date=params.get("check_in_date", request.check_in_date),
            check_out_date=params.get("check_out_date", request.check_out_date),
            adults=params.get("adults", request.adults),
            total_results=info.get("total_results"),
            hotels=[Hotel.from_api_response(h) for h in data.get("properties", [])],
        )
