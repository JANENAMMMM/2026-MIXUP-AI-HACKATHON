import { createFileRoute } from "@tanstack/react-router";
import TravelPlannerApp from "@/components/travel/TravelPlannerApp";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "AI 여행 플래너 — 채팅으로 완성되는 맞춤 여행" },
      {
        name: "description",
        content:
          "채팅 한 번으로 날짜·숙소·동선·예산까지 자동 설계되는 AI 여행 플래너 데모.",
      },
      { property: "og:title", content: "AI 여행 플래너" },
      {
        property: "og:description",
        content: "채팅으로 완성되는 맞춤 여행 일정.",
      },
    ],
  }),
  component: Index,
});

function Index() {
  return <TravelPlannerApp />;
}
