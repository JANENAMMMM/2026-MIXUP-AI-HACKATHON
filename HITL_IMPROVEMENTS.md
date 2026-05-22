# Human-in-the-Loop 개선 제안

## 현재 HITL 구조

```
사용자 입력
  → [명확화 카드] 예산 / 인원 / 숙소 선호  ← HITL 1 (단순 선택)
  → 파이프라인 실행
  → [날짜 선택] 3개 후보 중 선택           ← HITL 2
  → [호텔 필터] 정렬·등급·시설 선택        ← HITL 3
  → [호텔 선택] 10개 후보 중 선택          ← HITL 4
  → 최종 일정 출력
       ↳ "다시 시작" 버튼만 존재            ← 피드백 불가 (완전 단절)
```

### 현재의 문제
- 입력이 AI에게 잘못 파싱되어도 사용자가 교정할 방법 없음
- 중간 결과(날짜·호텔)가 마음에 안 들어도 "조건 바꿔서 재검색" 불가
- 최종 일정이 나온 이후에는 전체를 버리고 처음부터 다시 해야 함
- 장소 선호(활동 유형, 음식 취향)가 전혀 반영되지 않음

---

## 개선 포인트 (우선순위 순)

### 🔴 Priority 1 — 일정 피드백 루프 (가장 임팩트 큼)

**What**: 최종 일정 하단에 자유 텍스트 입력창 추가.  
"2일차가 너무 빡빡해 줄여줘", "레스토랑이 너무 비싸", "실내 활동 더 넣어줘" 등 자연어 피드백을 받아 synthesizer만 재실행.

**Why 임팩트**: 심사위원이 실제로 입력해보고 변화를 확인할 수 있는 유일한 구간. 나머지 HITL은 선택 UI이지만, 이건 진짜 "AI와 대화"처럼 보임.

**구현 방법**:

```python
# api/routes/plan.py 에 새 엔드포인트 추가
@router.post("/plan/refine")
async def refine_plan(req: RefineRequest) -> PlanResponse:
    # thread_id로 기존 state 복원
    # state["messages"]에 HumanMessage(content=feedback) 추가
    # synthesizer 노드만 재실행 (state 나머지는 유지)
```

```python
# src/agent/nodes/synthesizer_node.py
# 기존 state에 refinement_feedback 필드 추가
# synthesizer 프롬프트에 "이전 일정에 대한 사용자 피드백: {feedback}" 삽입
```

```typescript
// 프론트엔드: Itinerary 컴포넌트 하단에 FeedbackInput 추가
// 텍스트 입력 → POST /api/plan/refine → 새 일정으로 교체 (애니메이션)
```

**예상 소요 시간**: 45~60분  
**구현 리스크**: 낮음 — synthesizer를 단독으로 재실행하는 패턴이 깔끔함

---

### 🟡 Priority 2 — 인텐트 확인 카드

**What**: orchestrator가 의도를 파싱한 직후, "이렇게 이해했어요" 카드를 보여주고 틀린 항목만 수정 가능.

```
🗺 목적지: 제주도
📅 일정: 6월 20일 ~ 23일 (3박 4일)
👥 인원: 2명
💰 예산: 100만원

[맞아요 →]  [수정할게요]
```

**Why 임팩트**: "AI가 내 말을 제대로 이해했는지" 확인 욕구 충족. 파싱 오류를 초기에 잡아서 이후 전체 파이프라인이 올바르게 실행됨.

**구현 방법**:

```python
# orchestrator 노드 실행 후 interrupt() 삽입
# interrupt_val = {"type": "intent_confirm", "intent": parsed_intent}
# 사용자가 "맞아요" → Command(resume="ok")
# 수정 → Command(resume=json.dumps(corrected_intent))
```

**예상 소요 시간**: 40분  
**구현 리스크**: 중간 — intent 구조 변경이 downstream에 영향 없는지 확인 필요

---

### 🟡 Priority 3 — 장소 선호도 인터럽트

**What**: place_node 실행 전에 활동 유형과 음식 취향을 카드로 물어봄.

```
🎯 어떤 활동을 선호하세요? (복수 선택)
[🌿 자연·야외]  [🏛 문화·역사]  [🛍 쇼핑]  [🎢 체험·액티비티]  [🌙 야경·나이트라이프]

🍽 음식 취향은요? (복수 선택)
[🥩 고기]  [🐟 해산물]  [☕ 카페·브런치]  [🍜 현지식]  [🌱 채식]
```

**Why 임팩트**: "왜 내가 싫어하는 음식점이 나왔지?"를 예방. 호텔 prefs와 동일한 패턴이라 구현 빠름.

**구현 방법**:

```python
# stay_node.py와 동일한 패턴으로 place_prefs_node 추가
# graph: hotel_select → place_prefs → place_node
# place_node에서 state["place_prefs"]를 읽어 LLM 큐레이션 프롬프트에 반영
#   "사용자 선호 활동: 자연, 문화 / 음식 취향: 해산물, 카페"
```

**예상 소요 시간**: 30분  
**구현 리스크**: 낮음 — hotel_prefs 패턴 그대로 복붙 후 스키마만 변경

---

### 🟢 Priority 4 — "조건 바꿔서 재검색" 버튼

**What**: 날짜 선택 카드와 호텔 선택 카드 하단에 "마음에 드는 게 없어요 → 다시 검색" 버튼 추가.

- 날짜 카드: "다른 시기로 검색" → 목표 월(month) 조건 다시 물어보고 date_compute 재실행
- 호텔 카드: "조건 바꿔서 다시 검색" → hotel_prefs 인터럽트로 돌아가 hotel_compute 재실행

**Why 임팩트**: 현재는 마음에 드는 옵션이 없으면 처음부터 다시 해야 함. 중간 재시도 경험.

**구현 방법**:

```python
# /api/plan/restart_stage 엔드포인트 추가
# thread_id + stage("date"|"hotel") 받아서 해당 compute 노드부터 재실행
# LangGraph Command(goto="date_compute") 패턴 사용
```

**예상 소요 시간**: 50분  
**구현 리스크**: 높음 — LangGraph 그래프 재진입 로직이 까다로움. 시간 부족 시 프론트에서 "처음부터" 버튼으로 대체 가능.

---

## 1시간 구현 권장 조합

| 상황 | 구현 항목 |
|------|-----------|
| **시간이 1시간 있음** | Priority 1 (일정 피드백 루프) 단독 |
| **시간이 1.5시간 있음** | Priority 1 + Priority 3 (장소 선호도) |
| **발표까지 여유 있음** | Priority 1 + 2 + 3 전부 |

Priority 1 단독이 가장 인상적. 심사위원이 직접 "레스토랑 바꿔줘"를 입력하고 AI가 즉시 반응하는 장면이 가장 강력한 데모.

---

## 백엔드 state 필드 추가 예상 목록

```python
class AgentState(TypedDict):
    # 기존 필드들 ...
    
    # Priority 1 추가
    refinement_feedback: str          # 사용자 일정 피드백 텍스트
    
    # Priority 2 추가
    intent_confirmed: bool            # 인텐트 확인 여부
    
    # Priority 3 추가
    place_prefs: dict                 # 활동 유형, 음식 취향
```

---

## 프론트엔드 컴포넌트 추가 예상 목록

| 컴포넌트 | 역할 | 연관 Priority |
|----------|------|---------------|
| `ItineraryFeedbackInput` | 일정 하단 피드백 텍스트 입력 + 전송 | P1 |
| `IntentConfirmCard` | AI가 파싱한 인텐트 표시 + 수정 버튼 | P2 |
| `PlacePrefsCard` | 활동/음식 취향 다중 선택 (HotelPrefsCard 변형) | P3 |
| `RestartStageButton` | 날짜·호텔 카드 하단 "재검색" 버튼 | P4 |
