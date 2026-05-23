# LangGraph 에이전트 노드 역할 설명

이 문서는 여행 플래닝 시스템의 LangGraph에 포함된 9개 노드의 역할과 동작 방식을 설명합니다.

## 그래프 흐름

```
START 
  ↓
intent_router (의도 분석)
  ↓
date_compute (날짜 계산)
  ├─ 후보 있음 → date_select (날짜 선택) → weather
  └─ 후보 없음 → weather (날씨 조회)
  ↓
hotel_prefs (호텔 선호도)
  ↓
hotel_compute (호텔 계산)
  ├─ 선호 호텔 있음 → place
  └─ 검색 필요 → hotel_select (호텔 선택) → place
  ↓
place (장소 검색)
  ↓
synthesizer (일정 종합)
  ↓
END
```

---

## 1. intent_router (의도 라우팅)

**파일**: `src/agent/nodes/intent_router.py`

### 역할
사용자의 자연어 입력에서 여행 정보를 추출하는 첫 번째 노드입니다.

### 주요 기능
- **LLM을 이용한 정보 추출**: Claude를 사용하여 사용자 메시지 분석
- **추출되는 정보**:
  - 목적지 (destination)
  - 체크인/체크아웃 날짜 (check_in, check_out) — 날짜가 확정되지 않으면 공백
  - 예산 (budget) — 원화 단위로 변환
  - 인원 수 (adults)
  - 숙박 기간 (trip_nights)
  - 목표 월 (target_months) — 날짜가 미정인 경우 해당 월 지정 (YYYYMM 형식)
  - 직항 선호 (prefer_nonstop)
  - 선호 호텔명 (preferred_hotel)

### 상태 변경
- `intent`: 추출된 여행 정보 저장
- `date_fixed`: 날짜가 확정되었는지 여부 (boolean)

### 특이사항
- 날짜가 'M/D' 형식이면 현재 연도를 붙여 'YYYY-MM-DD'로 변환
- 날짜가 완전히 확정되지 않은 경우 (예: "7월 중", "여름에") `date_fixed=false` 설정
- 이를 통해 이후 date_compute 노드에서 여러 날짜 후보를 생성하도록 라우팅

---

## 2. date_compute (날짜 계산 및 항공료 조회)

**파일**: `src/agent/nodes/date_optimizer.py`

### 역할
여행 적합 날짜를 계산하고 항공료 정보를 수집하는 노드입니다.

### 주요 기능
- **날짜 후보 생성**:
  - `date_fixed=true`: 사용자가 지정한 날짜만 사용
  - `date_fixed=false`: 목표 월의 모든 주간 조합 생성
  
- **항공료 조회** (병렬 처리):
  - 국내/국제 여행 구분
  - SerpAPI를 통한 실시간 항공료 검색
  - 각 항공편의 시간대 페널티 적용 (새벽/야간 감점)
  
- **날씨 데이터 기반 평가**:
  - 각 날짜 후보에 대해 기상 예보 수집
  - 우천일 다음날 체크인은 점수 감점
  
- **날짜 랭킹**:
  - 항공료 + 날씨 + 시간대 페널티 기반으로 점수 계산
  - 상위 3개 후보를 `candidate_dates`로 저장

### 상태 변경
- `check_in`, `check_out`: 최상 추천 날짜 업데이트
- `candidate_dates`: 상위 3개 추천 날짜 (사용자 검토용)
- `flight_cost`: 선택된 항공권 비용
- `weather_summary`: 해당 기간 날씨 정보
- `is_rainy`: 우천 여부

### Interrupt 트리거
- 최상 추천 날짜 외에도 다른 후보가 있으면 `date_select` 노드로 라우팅

---

## 3. date_select (날짜 선택)

**파일**: `src/agent/nodes/date_optimizer.py`

### 역할
사용자가 여러 날짜 후보 중에서 선택하도록 인터럽트를 발생시키는 노드입니다.

### 주요 기능
- **사용자 인터럽트**: LangGraph interrupt() 호출
- **선택 항목**:
  - 상위 3개 날짜 후보 표시
  - 각 후보에 대해 점수와 추천 사유 표시
  
- **선택 후 상태 업데이트**:
  - 사용자가 선택한 날짜를 `check_in`, `check_out`에 반영
  - 해당 날짜의 항공료와 기상 정보 업데이트

### 특이사항
- **재계산 없음**: 이미 date_compute에서 계산한 정보만 사용
- API 이중 호출 방지로 성능 최적화

---

## 4. weather (날씨 조회)

**파일**: `src/agent/nodes/weather_node.py`

### 역할
여행 기간 동안의 일일 날씨 정보를 조회하고 정리하는 노드입니다.

### 주요 기능
- **재사용 로직**: 
  - date_compute에서 이미 계산한 날씨가 있으면 재사용
  - 새로운 날짜 선택 후 필요시에만 재조회
  
- **일일 날씨 정보 수집**:
  - 최고/최저 기온
  - 강수 확률
  - 강우량 (mm)
  
- **강우 판정**:
  - 강수확률 ≥ 50% 또는 강우량 > 1mm → `is_rainy=true`

### 상태 변경
- `is_rainy`: 기간 중 우천 여부
- `weather_summary`: 일일 날씨를 정렬한 텍스트

### 특이사항
- 체크인 날짜가 미확정이면 날씨 조회 스킵
- 범위 초과 날짜는 "예보 없음"으로 표시

---

## 5. hotel_prefs (호텔 선호도 설정)

**파일**: `src/agent/nodes/stay_node.py`

### 역할
사용자의 호텔 검색 필터 조건을 설정하는 인터럽트 노드입니다.

### 주요 기능
- **사용자 인터럽트**: 호텔 검색 필터 옵션 제시
- **필터 옵션**:
  - `sort_by`: 별점, 가격, 리뷰 수 등 정렬 기준
  - `property_types`: 호텔, 펜션, 리조트 등 숙소 유형
  - 예산 범위, 별점 최소값 등
  
- **선호 호텔 처리**:
  - intent_router에서 사용자가 특정 호텔명 언급 → 직접 hotel_compute로 건너뛰고 이 노드 스킵

### 상태 변경
- `hotel_prefs`: 사용자 선택 필터 정보

### 특이사항
- 선호 호텔이 명시된 경우, 호텔 검색 프로세스 단축
- 이미 알고 있는 호텔을 빠르게 예약하려는 사용자를 지원

---

## 6. hotel_compute (호텔 검색 및 비용 계산)

**파일**: `src/agent/nodes/stay_node.py`

### 역할
Google Hotels API를 통해 호텔을 검색하고 숙박 비용을 계산하는 노드입니다.

### 주요 기능
- **호텔 검색**:
  - 목적지, 체크인/체크아웃 날짜, 인원 수 기반 검색
  - 사용자 필터(`hotel_prefs`) 적용
  - 선호 호텔명이 있으면 직접 검색
  
- **비용 계산**:
  - 1박 가격 × 숙박 기간 = 총 숙박비
  - 잔여 예산 계산: `remaining_budget = total_budget - flight_cost - hotel_cost`
  
- **결과 저장**:
  - 검색된 호텔 목록 (5~10개)
  - 선택된 호텔명, 주소, 이미지, 어메니티 등

### 상태 변경
- `hotel_list`: 검색된 호텔 목록
- `hotel_name`, `hotel_address`: 최종 선택 호텔 정보
- `hotel_cost`: 총 숙박비
- `remaining_budget`: 식비/관광용 잔여 예산

### Interrupt 트리거
- 선호 호텔이 없으면 `hotel_select` 노드로 라우팅하여 사용자 선택 대기
- 선호 호텔이 있거나 선택 완료 시 `place` 노드로 진행

### 특이사항
- Mock 호텔 데이터 지원 (API 실패 시 기본값)
- 예산 대비 호텔 비용 자동 계산 (예산의 60%)

---

## 7. hotel_select (호텔 선택)

**파일**: `src/agent/nodes/stay_node.py`

### 역할
hotel_compute에서 검색한 호텔 목록 중에서 사용자가 하나를 선택하도록 하는 인터럽트 노드입니다.

### 주요 기능
- **사용자 인터럽트**: 검색된 호텔 목록 표시
  - 각 호텔의 가격, 별점, 이미지, 어메니티 표시
  
- **선택 후 상태 업데이트**:
  - 선택된 호텔의 정보를 상태에 반영
  - 최종 숙박비 계산

### 특이사항
- **재계산 없음**: 이미 hotel_compute에서 검색한 정보만 사용
- API 이중 호출 방지로 성능 최적화

---

## 8. place (장소 검색 및 동선 최적화)

**파일**: `src/agent/nodes/place_node.py`

### 역할
여행지의 맛집과 명소를 검색하고, 최적의 이동 동선을 계산하는 노드입니다.

### 주요 기능
- **식당 검색**:
  - 지역 기반 식당 추천
  - 음식 종류, 평점 등 정보 수집
  
- **명소 검색**:
  - 관광지, 박물관, 공원 등 정보 수집
  - 위치 좌표 확보
  
- **최적 동선 계산**:
  - Haversine 공식으로 호텔-장소 간 거리 계산
  - Nearest Neighbor 그리디 알고리즘으로 방문 순서 최적화
  - 총 이동 거리 최소화
  
- **경로 정보 생성**:
  - 각 장소 간 거리 (km) 계산
  - 이동 수단 추천 (도보, 버스 등)

### 상태 변경
- `restaurants`: 검색된 식당 목록
- `attractions`: 검색된 명소 목록
- `optimized_route`: 최적화된 방문 순서 목록
- `route_note`: 경로 정보를 텍스트로 정렬

### 특이사항
- 국내/국제 여행 구분:
  - 국내: Naver Local API 사용
  - 국제: Google Places API 사용
- Mock 호텔에서는 위치 정보 조회 스킵 (정확도 확보)

---

## 9. synthesizer (최종 일정 생성)

**파일**: `src/agent/nodes/synthesizer_node.py`

### 역할
수집된 모든 정보를 LLM이 통합하여 최종 여행 일정을 생성하는 노드입니다.

### 주요 기능
- **정보 통합**:
  - 선택된 날짜, 호텔, 항공료, 예산 정보
  - 날씨 정보
  - 식당과 명소 목록
  - 최적화된 동선 정보
  
- **LLM 기반 일정 생성**:
  - Solar Pro3 LLM을 사용
  - GFM(GitHub Flavored Markdown) 테이블 형식으로 일정표 작성
  - 일일 단위 `## Day 1`, `## Day 2` 등으로 구분
  
- **출력 형식**:
  - 예산 현황 (항공권, 숙박비, 잔여 예산)
  - 날씨 정보
  - 추천 날짜 후보 (참고용)
  - 마크다운 테이블 형식 일정표:
    ```
    | 시간 | 장소 | 활동 | 이동 | 비고 |
    |------|------|------|------|------|
    | 10:00 | 장소명 | 활동 내용 | 도보 0.8km | — |
    ```

### 상태 변경
- `final_report`: 최종 생성된 여행 일정 (마크다운 형식)

### 제약 사항
- 목록에 없는 장소 임의 추가 금지
- 교통비, 식비, KTX 일정 등 추가 정보 추가 금지
- 정보 부족 항목은 "정보 없음"으로 표기
- ASCII 박스나 공백 정렬은 사용 금지 (GFM 파이프 테이블만 사용)

### 특이사항
- 최종 노드로 모든 정보를 종합하는 역할
- 사용자에게 보이는 최종 결과물 생성
- 재호출 없이 한 번만 실행됨

---

## 노드 간 데이터 흐름

### AgentState 구조
```python
{
    "messages": [...],                    # 대화 메시지 히스토리
    "intent": {...},                      # 여행 의도 정보
    "date_fixed": bool,                   # 날짜 확정 여부
    "candidate_dates": [...],             # 추천 날짜 후보
    "check_in": str,                      # 체크인 날짜 (YYYY-MM-DD)
    "check_out": str,                     # 체크아웃 날짜 (YYYY-MM-DD)
    "flight_cost": int,                   # 항공료
    "weather_summary": str,               # 날씨 정보
    "is_rainy": bool,                     # 우천 여부
    "hotel_prefs": dict,                  # 호텔 검색 필터
    "hotel_list": [...],                  # 호텔 검색 결과
    "hotel_name": str,                    # 선택된 호텔명
    "hotel_address": str,                 # 호텔 주소
    "hotel_cost": int,                    # 숙박비
    "remaining_budget": int,              # 잔여 예산
    "restaurants": [...],                 # 식당 목록
    "attractions": [...],                 # 명소 목록
    "optimized_route": [...],             # 최적화된 동선
    "route_note": str,                    # 동선 설명
    "final_report": str,                  # 최종 여행 일정 (마크다운)
}
```

---

## 핵심 설계 원칙

### 1. Interrupt 활용
- 사용자 선택이 필요한 노드에서만 interrupt 발생
- `date_select`, `hotel_prefs`, `hotel_select` 노드 활용

### 2. API 이중 호출 방지
- `*_compute` 노드: API 호출만 수행
- `*_select` 노드: State 읽기만 수행 (resume 시 재호출 없음)

### 3. 조건부 라우팅
- `date_compute` → `date_select` 또는 `weather` (후보 유무에 따라)
- `hotel_compute` → `place` 또는 `hotel_select` (선호 호텔 유무에 따라)

### 4. 정보 재사용
- `weather_node`: date_compute 계산 결과 재사용
- `date_select`, `hotel_select`: 이미 계산된 정보만 사용

### 5. 에러 처리
- API 실패 시 Mock 데이터 활용
- 범위 초과 날씨는 "예보 없음"으로 표시
- 호텔 위치 조회 실패 시 동선 계산 스킵

---

## 각 노드의 Interrupt 패턴

| 노드 | Interrupt | 역할 | 선택 항목 |
|------|-----------|------|----------|
| date_select | ✓ | 추천 날짜 3개 중 선택 | 1개 날짜 선택 |
| hotel_prefs | ✓ | 호텔 검색 필터 설정 | 가격, 별점, 유형 등 |
| hotel_select | ✓ | 검색 호텔 목록 중 선택 | 1개 호텔 선택 |
| intent_router | ✗ | 정보 추출만 (LLM) | 없음 |
| date_compute | ✗ | 계산만 수행 | 없음 |
| weather | ✗ | 조회만 수행 | 없음 |
| hotel_compute | ✗ | API 호출만 수행 | 없음 |
| place | ✗ | 검색 및 최적화 | 없음 |
| synthesizer | ✗ | LLM 통합 | 없음 |
