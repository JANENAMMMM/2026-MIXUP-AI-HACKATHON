import os
import requests

from .models import HotelSearchRequest, Hotel, HotelSearchResult

API_URL = "https://serpapi.com/search.json"

def search_google_hotels(api_key: str, request: HotelSearchRequest) -> HotelSearchResult:
    """Google Hotels API로 호텔을 검색한다.

    Args:
        api_key: SerpApi API 키 (os.getenv("SERPAPI_KEY"))
        request: 검색 조건 (HotelSearchRequest)

    Returns:
        HotelSearchResult - 호텔 목록과 검색 메타 정보
    """
    params = {
        "engine": "google_hotels",
        "q": request.q,
        "check_in_date": request.check_in_date,
        "check_out_date": request.check_out_date,
        "adults": request.adults,
        "children": request.children,
        "gl": request.gl,
        "hl": request.hl,
        "currency": request.currency,
        "api_key": api_key,
        "no_cache": str(request.no_cache).lower(),
    }

    optional = {
        "children_ages": request.children_ages,
        "sort_by": request.sort_by,
        "min_price": request.min_price,
        "max_price": request.max_price,
        "rating": request.rating,
        "hotel_class": request.hotel_class,
        "free_cancellation": request.free_cancellation,
        "special_offers": request.special_offers,
        "eco_certified": request.eco_certified,
        "vacation_rentals": request.vacation_rentals,
        "bedrooms": request.bedrooms,
        "bathrooms": request.bathrooms,
        "next_page_token": request.next_page_token,
    }
    for key, value in optional.items():
        if value is not None:
            params[key] = value

    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    status = data.get("search_metadata", {}).get("status")
    if status == "Error" or data.get("error"):
        raise RuntimeError(data.get("error", "SerpApi search failed"))

    return HotelSearchResult.from_api_response(data, request)


def print_hotel_results(result: HotelSearchResult, limit: int = 10) -> None:
    """HotelSearchResult를 콘솔에 출력한다."""
    print("=" * 80)
    print("Google Hotels Search Summary")
    print("=" * 80)
    print(f"Query           : {result.query}")
    print(f"Stay            : {result.check_in_date} -> {result.check_out_date}")
    print(f"Guests          : adults={result.adults}")
    print(f"Total Results   : {result.total_results}")
    print(f"Properties Count: {len(result.hotels)}")
    print()

    for idx, hotel in enumerate(result.hotels[:limit], start=1):
        amenities = ", ".join(hotel.amenities[:6])
        print(f"[{idx}] {hotel.name}")
        print(f"  Type           : {hotel.type}")
        print(f"  Hotel Class    : {hotel.hotel_class}")
        print(f"  Rating/Reviews : {hotel.overall_rating} / {hotel.reviews}")
        print(f"  Nightly Rate   : {hotel.rate_per_night}")
        print(f"  Total Rate     : {hotel.total_rate}")
        print(f"  Amenities      : {amenities}")
        print(f"  Property Token : {hotel.property_token}")
        print(f"  Details Link   : {hotel.details_link}")
        print()
