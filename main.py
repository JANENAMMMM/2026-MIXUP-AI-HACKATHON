# -*- coding: utf-8 -*-
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from src.weather import get_weather
from src.hotel import search_google_hotels, print_hotel_results, HotelSearchRequest
from src.tourist import search_places, search_local
from src.transport import search_flights, search_transit

USAGE = """\
사용법: python main.py <command> [args...]

  weather <city> <date>                  날씨 조회  (date: today 또는 YYYY-MM-DD)
  hotel   <query> <check_in> <check_out> 호텔 검색  (날짜 형식: YYYY-MM-DD)
  tourist <query>                        Google Places 관광지/식당 검색
  naver   <query>                        네이버 지역 검색
  flight  <dep_iata> <arr_iata> <date>   항공편 검색 (IATA 코드 예: ICN, NRT)
  transit <출발지> <도착지>              대중교통 경로 검색

예시:
  python main.py weather 서울 today
  python main.py hotel "Seoul hotels" 2026-06-01 2026-06-03
  python main.py tourist "Tokyo Shibuya restaurants"
  python main.py naver "해운대 횟집"
  python main.py flight ICN NRT 2026-06-01
  python main.py transit 서울역 부산역
"""


def _cmd_weather(args: list[str]) -> None:
    city = args[0] if args else "서울"
    date = args[1] if len(args) > 1 else "today"
    get_weather(city, date)


def _cmd_hotel(args: list[str]) -> None:
    api_key = os.getenv("SERPAPI_KEY")
    if not api_key:
        raise SystemExit("SERPAPI_KEY 환경변수가 필요합니다.")
    request = HotelSearchRequest(
        q=args[0] if args else "Seoul hotels",
        check_in_date=args[1] if len(args) > 1 else "2026-06-01",
        check_out_date=args[2] if len(args) > 2 else "2026-06-03",
    )
    result = search_google_hotels(api_key, request)
    print_hotel_results(result, limit=5)


def _cmd_tourist(args: list[str]) -> None:
    query = args[0] if args else "Tokyo Shibuya restaurants"
    places = search_places(query)
    print(f"총 {len(places)}개 장소\n" + "-" * 30)
    for i, p in enumerate(places, 1):
        print(f"[{i}] {p.name}")
        print(f"    {p.address}")


def _cmd_naver(args: list[str]) -> None:
    query = args[0] if args else "해운대 횟집"
    items = search_local(query)
    print(f"총 {len(items)}개 장소\n" + "-" * 30)
    for i, p in enumerate(items, 1):
        print(f"[{i}] {p.title}  [{p.category}]")
        print(f"    {p.road_address or p.address}")
        if p.telephone:
            print(f"    {p.telephone}")


def _cmd_flight(args: list[str]) -> None:
    dep = args[0] if args else "ICN"
    arr = args[1] if len(args) > 1 else "NRT"
    date = args[2] if len(args) > 2 else "2026-06-01"
    result = search_flights(dep, arr, date)
    if result.error:
        print("오류:", result.error)
        return
    for i, f in enumerate(result.flights, 1):
        print(
            f"[{i}] {f.airline} {f.flight_number} | "
            f"{f.departure_time} → {f.arrival_time} ({f.duration_minutes}분, 경유 {f.stops}회)"
        )
        print(f"    1인 {f.price_per_person:,}원 / 총 {f.total_price:,}원")


def _cmd_transit(args: list[str]) -> None:
    start = args[0] if args else "서울역"
    end = args[1] if len(args) > 1 else "부산역"
    result = search_transit(start, end)
    if result.error:
        print("오류:", result.error)
        return
    for i, r in enumerate(result.routes, 1):
        print(f"[{i}] {r.summary} | {r.formatted_duration} | {r.distance}")
        if r.start_time:
            print(f"    {r.start_time} → {r.end_time}")
        if r.cost is not None:
            print(f"    요금: {r.cost:,}{r.currency}")


COMMANDS = {
    "weather": _cmd_weather,
    "hotel": _cmd_hotel,
    "tourist": _cmd_tourist,
    "naver": _cmd_naver,
    "flight": _cmd_flight,
    "transit": _cmd_transit,
}


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(USAGE)
        return
    COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
