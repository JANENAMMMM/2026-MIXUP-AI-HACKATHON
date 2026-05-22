"""
tools/google_flights.py 직접 테스트 (에이전트 레이어 없이 SerpApi만 호출)
실행: python test_transport.py
"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from tools.google_flights import search_flights


def main():
    print("=== 항공편 검색 테스트: ICN → PUS (왕복, 3인) ===\n")

    result = search_flights(
        departure_id="ICN",
        arrival_id="PUS",
        outbound_date="2026-05-30",
        return_date="2026-05-31",
        adults=3,
    )

    if "error" in result:
        print("오류:", result["error"])
        return

    flights = result["flights"]
    print(f"검색된 항공편 {len(flights)}개\n")

    for i, f in enumerate(flights, 1):
        print(
            f"{i}. {f['airline']} {f['flight_number']} | "
            f"{f['departure_time']} → {f['arrival_time']} "
            f"({f['duration_minutes']}분, 경유 {f['stops']}회)"
        )
        print(f"   1인 {f['price_per_person']:,}원 / 총 {f['total_price']:,}원")
        print(f"   예약: {f['booking_url']}\n")

    print("[전체 JSON]")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
