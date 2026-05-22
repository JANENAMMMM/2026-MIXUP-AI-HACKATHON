from langchain_core.messages import HumanMessage, SystemMessage

from src.agent.state import AgentState


def make_synthesizer_node(llm):
    def synthesizer_node(state: AgentState) -> dict:
        intent = state["intent"]
        candidates = state.get("candidate_dates", [])

        candidate_text = ""
        if candidates:
            candidate_text = "\n[ 추천 날짜 TOP 3 ]\n"
            for i, c in enumerate(candidates, 1):
                candidate_text += (
                    f"  {i}위) {c['check_in']} ~ {c['check_out']} "
                    f"| 점수 {c['score']} | {c['reason']}\n"
                )

        places_text = "[ 수집된 장소 ]\n"
        places_text += f"숙소: {state.get('hotel_name')} ({state.get('hotel_address')})\n"
        for r in state.get("restaurants", []):
            desc = f" — {r['description']}" if r.get("description") else ""
            places_text += f"맛집: {r['title']} | {r['address']} | {r['category']}{desc}\n"
        for a in state.get("attractions", []):
            desc = f" — {a['description']}" if a.get("description") else ""
            places_text += f"명소: {a['title']} | {a['address']} | {a['category']}{desc}\n"

        system = SystemMessage(content=(
            "너는 전문 여행 플래너야. "
            "[수집된 장소] 목록에 있는 장소만 사용해서 동선이 효율적인 여행 일정을 짜줘. "
            "목록에 없는 장소, 교통수단 가격, 식비, KTX 일정 등은 절대 임의로 추가하지 마. "
            "정보가 부족한 항목은 '정보 없음'으로 표기해.\n\n"
            "출력 형식 규칙 (반드시 준수):\n"
            "- 결과는 **한국어 마크다운**으로 출력.\n"
            "- 일정표는 반드시 **GFM 마크다운 표** 형식으로 작성. 예시:\n"
            "  | 시간 | 장소 | 활동 | 이동 | 비고 |\n"
            "  |------|------|------|------|------|\n"
            "  | 10:00 | 장소명 | 활동 내용 | 도보 0.8km | — |\n"
            "- 표 헤더 구분선(|---|)은 반드시 포함.\n"
            "- [위치 기반 최적 동선]이 제공된 경우 → 해당 순서를 일정표에 그대로 반영하고, "
            "  이동 거리(km)를 '이동' 열에 표기하라.\n"
            "- 예산 현황과 날씨 정보를 일정 상단에 ## 섹션으로 포함.\n"
            "- 날별로 ## Day 1, ## Day 2 형식으로 구분.\n"
            "- ASCII 박스(+--)나 공백 정렬 표는 절대 사용하지 마. GFM 파이프 표만 사용."
        ))

        route_note = state.get("route_note", "")

        user_content = (
            f"목적지: {intent['destination']}\n"
            f"일정: {intent['check_in']} ~ {intent['check_out']}\n"
            f"예산: {intent['budget']:,}원 (숙박 후 잔여: {state.get('remaining_budget', 0):,}원)\n"
            f"날씨: {state.get('weather_summary', '')}\n"
            f"{candidate_text}\n"
            f"{places_text}"
            + (f"\n{route_note}" if route_note else "")
        )

        print(f"\n📝 [5/5] 일정 생성 중 — Solar Pro3 호출...")
        response = llm.invoke([system, HumanMessage(content=user_content)])
        print("  ✓ 완료\n")
        return {"final_report": response.content}

    return synthesizer_node
