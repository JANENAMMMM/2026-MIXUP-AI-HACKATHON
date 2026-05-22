"""
tools/google_transit.py 직접 테스트
실행: uv run python test_transit.py
"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

from tools.google_transit import search_transit


def main():
    print("=== 대중교통 경로 테스트: 서울역 → 부산역 ===\n")

    result = search_transit(
        start_addr="서울역",
        end_addr="부산역",
        prefer="train",
    )

    if "error" in result:
        print("오류:", result["error"])
        return

    routes = result["routes"]
    print(f"검색된 경로 {len(routes)}개\n")

    for i, r in enumerate(routes, 1):
        print(f"{i}. {r['summary']} | {r['formatted_duration']} | {r['distance']}")
        if r["start_time"]:
            print(f"   {r['start_time']} → {r['end_time']}")
        if r["cost"] is not None:
            print(f"   요금: {r['cost']:,}{r['currency']}")
        for trip in r["trips"]:
            if trip["mode"] == "WALKING":
                continue
            print(
                f"   [{trip['title']}] {trip['start_stop']['name']}({trip['start_stop']['time']})"
                f" → {trip['end_stop']['name']}({trip['end_stop']['time']})"
                f" | {trip['service']}"
            )
        print()

    print("[전체 JSON]")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
