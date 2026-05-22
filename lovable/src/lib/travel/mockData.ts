import stay1 from "@/assets/stay-1.jpg";
import stay2 from "@/assets/stay-2.jpg";
import stay3 from "@/assets/stay-3.jpg";

export const EXAMPLE_PROMPTS = [
  "6월 말 제주도 2박3일 일정 짜줘",
  "다음 달 부산 혼자 여행, 예산 50만원",
  "7월 초 강릉, 이 카페 꼭 포함해줘 ☕",
];

export const BUDGET_OPTIONS = ["30만 이하", "30~70만", "70~150만", "150만+"];
export const PEOPLE_OPTIONS = ["혼자", "2명", "3~4명", "5명+"];
export const STAY_OPTIONS = [
  { label: "바다 전망", emoji: "🌊" },
  { label: "자연 속", emoji: "🌲" },
  { label: "시내 중심", emoji: "🏙️" },
  { label: "조용한 외곽", emoji: "🤫" },
];

export const DATE_PROPOSALS = [
  { id: "d1", label: "6/20(금) – 6/22(일)", note: "맑음 · 평균 23°C · 성수기 진입 전" },
  { id: "d2", label: "6/27(금) – 6/29(일)", note: "맑음/구름 · 평균 24°C · 추천 ⭐" },
  { id: "d3", label: "6/29(일) – 7/1(화)", note: "장마 시작 가능 · 실내 일정 추천" },
];

export const STAY_PROPOSALS = [
  {
    id: "s1",
    name: "협재 오션뷰 펜션",
    image: stay1,
    price: 140000,
    rating: 4.8,
    tags: ["오션뷰", "조식 포함", "주차"],
  },
  {
    id: "s2",
    name: "함덕 씨사이드 호텔",
    image: stay2,
    price: 210000,
    rating: 4.7,
    tags: ["풀 오션뷰", "수영장", "조식"],
  },
  {
    id: "s3",
    name: "구좌 한옥 스테이",
    image: stay3,
    price: 175000,
    rating: 4.9,
    tags: ["한옥", "프라이빗", "고요함"],
  },
];

export const PLACES = [
  { name: "성산일출봉", type: "명소", indoor: false },
  { name: "협재해변", type: "명소", indoor: false },
  { name: "흑돼지 명가 (돈사돈)", type: "맛집", indoor: true },
  { name: "오설록 티 뮤지엄", type: "카페·실내", indoor: true },
  { name: "월정리 해변 카페거리", type: "카페", indoor: false },
  { name: "제주 민속촌", type: "체험·실내", indoor: true },
];

export type ItineraryRow = {
  time: string;
  place: string;
  activity: string;
  transport: string;
  cost: number;
};

export const ITINERARY: { day: string; date: string; rows: ItineraryRow[] }[] = [
  {
    day: "Day 1",
    date: "6/27 (금)",
    rows: [
      { time: "10:30", place: "제주국제공항", activity: "도착 · 렌터카 픽업", transport: "도보", cost: 85000 },
      { time: "12:00", place: "돈사돈 (노형)", activity: "흑돼지 점심", transport: "렌터카 15분", cost: 58000 },
      { time: "14:00", place: "협재해변", activity: "산책 · 인생샷", transport: "렌터카 40분", cost: 0 },
      { time: "16:00", place: "월정리 카페거리", activity: "오션뷰 카페 타임", transport: "렌터카 35분", cost: 18000 },
      { time: "18:30", place: "협재 오션뷰 펜션", activity: "체크인 · 휴식", transport: "렌터카 25분", cost: 140000 },
      { time: "20:00", place: "근처 해산물 식당", activity: "전복뚝배기 저녁", transport: "도보 5분", cost: 64000 },
    ],
  },
  {
    day: "Day 2",
    date: "6/28 (토)",
    rows: [
      { time: "07:30", place: "성산일출봉", activity: "일출 트레킹", transport: "렌터카 1시간", cost: 10000 },
      { time: "10:00", place: "광치기 해변 식당", activity: "성게비빔밥 아침", transport: "도보 10분", cost: 42000 },
      { time: "12:00", place: "섭지코지", activity: "산책 · 휘닉스 둘러보기", transport: "렌터카 15분", cost: 0 },
      { time: "14:30", place: "오설록 티 뮤지엄", activity: "티 클래스 (실내)", transport: "렌터카 1시간", cost: 36000 },
      { time: "17:00", place: "협재 오션뷰 펜션", activity: "휴식 · 노을 감상", transport: "렌터카 30분", cost: 140000 },
      { time: "19:00", place: "한림 흑돼지 BBQ", activity: "저녁", transport: "렌터카 10분", cost: 72000 },
    ],
  },
  {
    day: "Day 3",
    date: "6/29 (일)",
    rows: [
      { time: "09:00", place: "협재 오션뷰 펜션", activity: "체크아웃", transport: "렌터카", cost: 0 },
      { time: "09:30", place: "한림 카페 '앤트러사이트'", activity: "브런치", transport: "렌터카 10분", cost: 28000 },
      { time: "11:00", place: "오라동 청보리밭", activity: "산책 · 사진", transport: "렌터카 40분", cost: 0 },
      { time: "13:00", place: "제주공항 근처 고기국수", activity: "마지막 점심", transport: "렌터카 30분", cost: 24000 },
      { time: "15:00", place: "제주국제공항", activity: "렌터카 반납 · 출국", transport: "도보", cost: 0 },
    ],
  },
];

export const TOTAL_COST = ITINERARY.reduce(
  (sum, d) => sum + d.rows.reduce((s, r) => s + r.cost, 0),
  0,
);

export const won = (n: number) => `₩${n.toLocaleString("ko-KR")}`;