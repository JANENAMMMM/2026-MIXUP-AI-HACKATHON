import os

from langgraph.types import interrupt

from src.agent.state import AgentState
from src.hotel.search import search_google_hotels
from src.hotel.models import HotelSearchRequest, Hotel

HOTEL_BUDGET_RATIO = 0.6  # 총 예산의 최대 60%를 숙박에 사용

_MOCK_HOTELS = [
    {
        "name": "해운대 그랜드 호텔 (Mock)",
        "address": "부산광역시 해운대구 해운대해변로 20",
        "description": "바다 전망과 조식 포함, 도보로 해운대 해변 접근 가능",
        "image_url": "https://example.com/mock1.jpg",
        "amenities": ["조식", "Wi-Fi", "피트니스", "무료 주차"],
        "details_link": "https://example.com/mock1",
        "cost": 150000,
        "rating": 4.5,
    },
    {
        "name": "파크 하얏트 부산 (Mock)",
        "address": "부산광역시 해운대구 해운대해변로 24",
        "description": "럭셔리 룸과 스파 시설, 도심 최고의 전망 제공",
        "image_url": "https://example.com/mock2.jpg",
        "amenities": ["스파", "실내 수영장", "바/라운지", "컨시어지"],
        "details_link": "https://example.com/mock2",
        "cost": 220000,
        "rating": 4.8,
    },
    {
        "name": "노보텔 앰배서더 부산 (Mock)",
        "address": "부산광역시 해운대구 우동 1411-1",
        "description": "가족 여행에 적합한 객실과 실내 수영장을 갖춘 합리적 가격대 호텔",
        "image_url": "https://example.com/mock3.jpg",
        "amenities": ["실내 수영장", "가족룸", "조식", "무료 Wi-Fi"],
        "details_link": "https://example.com/mock3",
        "cost": 120000,
        "rating": 4.2,
    },
]


def _parse_cost(raw: str | None) -> int:
    if not raw:
        return 0
    digits = "".join(filter(str.isdigit, raw))
    cost = int(digits) if digits else 0
    return cost if cost >= 10000 else 0


def search_hotel_candidates(intent: dict, max_per_night: int, limit: int = 10) -> list[dict]:
    """SerpAPI로 예산 이내 호텔 추천 후보를 검색한다 (최대 limit개). 실패 시 Mock 반환."""
    serpapi_key = os.getenv("SERPAPI_KEY")
    if not serpapi_key:
        print("  ✗ SERPAPI_KEY 없음 → Mock 데이터 사용")
        return _build_mock(intent)

    try:
        req = HotelSearchRequest(
            q=f"{intent['destination']} 호텔",
            check_in_date=intent["check_in"],
            check_out_date=intent["check_out"],
            adults=intent["adults"],
            max_price=max_per_night,
            gl="kr", hl="ko", currency="KRW", sort_by=3,
        )
        result = search_google_hotels(serpapi_key, req)
        if not result.hotels:
            raise ValueError("검색 결과 없음")

        candidates = []
        nights = max(intent.get("trip_nights", 1), 1)
        for h in result.hotels[:limit]:
            if h.total_rate:
                cost = _parse_cost(h.total_rate)
            else:
                cost = _parse_cost(h.rate_per_night) * nights
                
            candidates.append({
                "name": h.name,
                "address": h.address or "",
                "description": h.description or "",
                "image_url": h.thumbnail or "",
                "cost": cost,
                "rating": h.overall_rating or 0.0,
                "amenities": h.amenities[:4],
                "details_link": h.details_link or "",
            })
        return candidates

    except Exception as e:
        print(f"  ✗ SerpApi 실패 ({e}) → Mock 데이터 사용")
        return _build_mock(intent)


def _build_mock(intent: dict) -> list[dict]:
    """Mock 호텔 3곳 반환 (총 비용 기준으로 trip_nights 반영)."""
    nights = max(intent.get("trip_nights", 1), 1)
    return [
        {
            "name": h["name"],
            "address": h.get("address", ""),
            "description": h.get("description", ""),
            "image_url": h.get("image_url", ""),
            "amenities": h.get("amenities", []),
            "details_link": h.get("details_link", ""),
            "cost": h["cost"] * nights,
            "rating": h.get("rating", 0.0),
        }
        for h in _MOCK_HOTELS
    ]


def make_stay_node():
    def stay_node(state: AgentState) -> dict:
        intent = state["intent"]
        preferred = intent.get("preferred_hotel")
        budget = intent["budget"]
        nights = max(intent.get("trip_nights", 1), 1)
        adults = intent.get("adults", 1)
        # flight_cost: Naver/SerpAPI 모두 1인 왕복 기준이므로 adults 곱한 값이 들어옴
        flight_cost = intent.get("flight_cost", 0)

        print(f"\n🏨 [3/5] 숙소 확인 중 — {intent['destination']}")
        print(f"  예산 현황: 총 {budget:,}원 | 항공(왕복×{adults}인) {flight_cost:,}원 차감")

        after_flight = budget - flight_cost

        # Case 1: 선호 호텔 명시 → 가격 조회 없이 패스
        if preferred:
            print(f"  ✓ 선호 호텔 사용: {preferred} (숙박비 미확인)")
            return {
                "hotel_name": preferred,
                "hotel_address": "",
                "hotel_cost": 0,
                "remaining_budget": after_flight,
                "hotel_candidates": [],
            }

        # Case 2: 선호 없음 → 잔여 예산 기반 검색
        # 항공비가 이미 차감된 경우: 잔여의 90% 숙박 배분
        # 항공비 미확정(0)인 경우: 총 예산의 HOTEL_BUDGET_RATIO% 배분 (항공비 몫 확보)
        if flight_cost > 0:
            max_hotel_total = max(int(after_flight * 0.9), 0)
        else:
            max_hotel_total = int(budget * HOTEL_BUDGET_RATIO)
            print(f"  △ 항공비 미확정 — 총 예산의 {int(HOTEL_BUDGET_RATIO*100)}%를 숙박 상한으로 설정")

        max_per_night = max_hotel_total // nights
        print(f"  → 숙박 가용 {max_hotel_total:,}원 ({nights}박) → 1박 상한 {max_per_night:,}원")

        candidates = search_hotel_candidates(intent, max_per_night, limit=10)

        choice = interrupt({
            "type": "hotel_selection",
            "question": (
                f"숙소를 선택해주세요 "
                f"(1박 {max_per_night:,}원 이하 기준, {nights}박 총액 {max_hotel_total:,}원 이내):"
            ),
            "candidates": candidates,
        })

        try:
            idx = int(choice) - 1
            if not (0 <= idx < len(candidates)):
                idx = 0
        except (ValueError, TypeError):
            idx = 0

        chosen = candidates[idx]
        # hotel cost = 총 숙박비 (nights 기준 total_rate 또는 per_night * nights)
        hotel_cost = chosen["cost"]
        remaining = budget - flight_cost - hotel_cost
        print(
            f"  ✓ 선택: {chosen['name']} | 숙박 {hotel_cost:,}원({nights}박) | "
            f"잔여 예산: {budget:,} - {flight_cost:,}(항공) - {hotel_cost:,}(숙박) = {remaining:,}원"
        )

        return {
            "hotel_name": chosen["name"],
            "hotel_address": chosen.get("address", ""),
            "hotel_cost": hotel_cost,
            "remaining_budget": remaining,
            "hotel_candidates": candidates,
        }

    return stay_node
