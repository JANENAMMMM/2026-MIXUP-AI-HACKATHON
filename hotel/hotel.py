import os
from dotenv import load_dotenv
import requests
from pprint import pprint

load_dotenv()
API_URL = "https://serpapi.com/search.json"

def search_google_hotels(
    api_key: str,
    q: str,
    check_in_date: str,
    check_out_date: str,
    adults: int = 2,
    children: int = 0,
    children_ages: str | None = None,
    gl: str = "kr",
    hl: str = "ko",
    currency: str = "KRW",
    sort_by: int | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    rating: int | None = None,
    hotel_class: str | None = None,
    free_cancellation: bool | None = None,
    special_offers: bool | None = None,
    eco_certified: bool | None = None,
    property_types: str | None = None,
    amenities: str | None = None,
    brands: str | None = None,
    vacation_rentals: bool | None = None,
    bedrooms: int | None = None,
    bathrooms: int | None = None,
    next_page_token: str | None = None,
    no_cache: bool = False,
):
    params = {
        "engine": "google_hotels",
        "q": q,
        "check_in_date": check_in_date,
        "check_out_date": check_out_date,
        "adults": adults,
        "children": children,
        "gl": gl,
        "hl": hl,
        "currency": currency,
        "api_key": api_key,
        "no_cache": str(no_cache).lower(),
    }

    optional_params = {
        "children_ages": children_ages,
        "sort_by": sort_by,
        "min_price": min_price,
        "max_price": max_price,
        "rating": rating,
        "hotel_class": hotel_class,
        "free_cancellation": free_cancellation,
        "special_offers": special_offers,
        "eco_certified": eco_certified,
        "property_types": property_types,
        "amenities": amenities,
        "brands": brands,
        "vacation_rentals": vacation_rentals,
        "bedrooms": bedrooms,
        "bathrooms": bathrooms,
        "next_page_token": next_page_token,
    }

    for key, value in optional_params.items():
        if value is not None:
            params[key] = value

    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    status = data.get("search_metadata", {}).get("status")
    if status == "Error" or data.get("error"):
        raise RuntimeError(data.get("error", "SerpApi search failed"))

    return data



def print_hotel_results(data: dict, limit: int = 10):
    search_params = data.get("search_parameters", {})
    search_info = data.get("search_information", {})
    properties = data.get("properties", [])
    ads = data.get("ads", [])

    print("=" * 80)
    print("Google Hotels Search Summary")
    print("=" * 80)
    print(f"Query           : {search_params.get('q')}")
    print(f"Stay            : {search_params.get('check_in_date')} -> {search_params.get('check_out_date')}")
    print(f"Guests          : adults={search_params.get('adults')} children={search_params.get('children')}")
    print(f"Locale          : gl={search_params.get('gl')} hl={search_params.get('hl')} currency={search_params.get('currency')}")
    print(f"Total Results   : {search_info.get('total_results')}")
    print(f"Ads Count       : {len(ads)}")
    print(f"Properties Count: {len(properties)}")
    print()

    for idx, hotel in enumerate(properties[:limit], start=1):
        name = hotel.get("name")
        kind = hotel.get("type")
        rating = hotel.get("overall_rating")
        reviews = hotel.get("reviews")
        hotel_class = hotel.get("hotel_class") or hotel.get("extracted_hotel_class")
        rate = hotel.get("rate_per_night", {}).get("lowest")
        total = hotel.get("total_rate", {}).get("lowest")
        amenities = ", ".join(hotel.get("amenities", [])[:6])
        details_link = hotel.get("serpapi_property_details_link")
        property_token = hotel.get("property_token")

        print(f"[{idx}] {name}")
        print(f"  Type           : {kind}")
        print(f"  Hotel Class    : {hotel_class}")
        print(f"  Rating/Reviews : {rating} / {reviews}")
        print(f"  Nightly Rate   : {rate}")
        print(f"  Total Rate     : {total}")
        print(f"  Amenities      : {amenities}")
        print(f"  Property Token : {property_token}")
        print(f"  Details Link   : {details_link}")
        print()

    next_page_token = data.get("serpapi_pagination", {}).get("next_page_token")
    if next_page_token:
        print(f"Next Page Token  : {next_page_token}")


if __name__ == "__main__":
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        raise SystemExit("Please set the SERPAPI_KEY environment variable.")

    example_query = {
        "q": "Seoul hotels",
        "check_in_date": "2026-06-01",
        "check_out_date": "2026-06-03",
        "adults": 2,
        "children": 0,
        "children_ages": None,
        "gl": "kr",
        "hl": "ko",
        "currency": "KRW",
        "sort_by": 3,
        "min_price": None,
        "max_price": None,
        "rating": 8,
        "hotel_class": "3,4,5",
        "free_cancellation": True,
        "special_offers": True,
        "eco_certified": False,
    }

    results = search_google_hotels(api_key=api_key, **example_query)
    print_hotel_results(results, limit=10)

    # Uncomment to inspect the raw JSON structure.
    # pprint(results)