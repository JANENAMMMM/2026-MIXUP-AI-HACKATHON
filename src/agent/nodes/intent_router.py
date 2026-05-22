import json
from datetime import datetime, timedelta

from langchain_core.messages import HumanMessage, SystemMessage

from src.agent.state import AgentState, TravelIntent


def make_intent_router(llm):
    def intent_router(state: AgentState) -> dict:
        """자연어 입력에서 목적지/날짜/예산/인원을 추출한다.

        날짜가 명시되지 않으면 date_fixed=False로 표시해 date_optimizer로 라우팅한다.
        """
        user_msg = state["messages"][-1].content
        today = datetime.now().date()

        system = SystemMessage(content=(
            "너는 여행 정보 추출 AI야. 사용자 입력에서 아래 JSON을 추출해.\n"
            "규칙:\n"
            "- 날짜가 'M/D' 형식이면 올해 연도를 붙여 'YYYY-MM-DD'로 변환.\n"
            "- 날짜가 정확히 확정된 경우에만 date_fixed=true.\n"
            "- '7월 중', '여름에', '대충 7월', '7월쯤', '8월 초' 처럼 월이나 시기만 언급되면 "
            "date_fixed=false, target_months에 해당 월을 'YYYYMM' 형식으로 설정.\n"
            "- 날짜가 전혀 없거나 '미정'이면 date_fixed=false, target_months=[].\n"
            "- date_fixed=false면 check_in='', check_out='' 로 설정.\n"
            "- 숙박 기간이 언급되면 trip_nights에 설정 (예: '3박4일' → 3, '2박' → 2). 없으면 2.\n"
            "- 예산은 원화(KRW) 정수로 변환. 예: '100만원'→1000000, '150만원'→1500000, "
            "'50만원'→500000, '300만원'→3000000, '1000만원'→10000000, '200만원'→2000000.\n"
            "- 인원 정보 없으면 adults=1.\n"
            "- '직항', '경유 없이', '논스톱', '직항으로' 같은 표현이 있으면 prefer_nonstop=true. 없으면 false.\n"
            "- 사용자가 특정 호텔명을 언급하면 preferred_hotel에 설정 (예: '롯데호텔', '파크 하얏트'), 없으면 null.\n"
            f"- 오늘 날짜: {today}\n\n"
            "반드시 아래 JSON 형식만 출력 (설명 없이):\n"
            '{"destination":"런던","date_fixed":false,"check_in":"","check_out":"",'
            '"budget":3000000,"adults":1,"trip_nights":3,"target_months":["202607"],'
            '"prefer_nonstop":false,"preferred_hotel":null}'
        ))

        print("\n🧠 [1/5] 의도 분석 중...")
        response = llm.invoke([system, HumanMessage(content=user_msg)])
        raw = response.content.strip()
        if "```" in raw:
            raw = raw.split("```")[1].strip()
            if raw.startswith("json"):
                raw = raw[4:].strip()

        data = json.loads(raw)
        date_fixed: bool = bool(data.get("date_fixed", True))
        trip_nights: int = int(data.get("trip_nights", 2))

        if date_fixed:
            check_in = data.get("check_in", today.isoformat())
            check_out = data.get("check_out", (today + timedelta(days=trip_nights)).isoformat())
        else:
            check_in = ""
            check_out = ""

        target_months: list = data.get("target_months", [])

        prefer_nonstop: bool = bool(data.get("prefer_nonstop", False))
        preferred_hotel = data.get("preferred_hotel") or None

        intent: TravelIntent = {
            "destination": data.get("destination", "서울"),
            "check_in": check_in,
            "check_out": check_out,
            "budget": int(data.get("budget", 500000)),
            "adults": int(data.get("adults", 1)),
            "trip_nights": trip_nights,
            "target_months": target_months,
            "prefer_nonstop": prefer_nonstop,
            "preferred_hotel": preferred_hotel,
        }
        date_str = f"{check_in} ~ {check_out}" if date_fixed else "미정"
        print(f"  ✓ 목적지: {intent['destination']} | 날짜: {date_str} | 예산: {intent['budget']:,}원 | {trip_nights}박")
        return {"intent": intent, "date_fixed": date_fixed}

    return intent_router
