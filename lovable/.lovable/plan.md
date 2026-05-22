# AI 여행 플래너 — Demo Build Plan

A fully click-through Korean travel planning demo. No backend, no real AI calls — all state is local React state with `setTimeout`-driven animations to simulate the agent pipeline.

## Scope assumptions
- Single conversation, no persistence (demo). No thread list, no DB, no auth.
- All "AI" responses, agent steps, and itinerary data are hardcoded mock data tuned to the 제주도 · 2박3일 · 바다 전망 · 100만원 scenario.
- Any example chip or freeform input advances into the same scripted flow (the demo is deterministic).

## Visual system
- Light modern theme. White background, soft gray borders, subtle shadows, rounded-2xl cards.
- Korean UI throughout. Pretendard-style system font stack.
- Centered column, `max-w-[800px]`, full-screen height, sticky chat input at bottom.
- Tailwind + shadcn/ui (Button, Card, Badge, Input/Textarea, ScrollArea, Separator) + Lucide icons.
- Status colors via semantic tokens added to `src/styles.css`: `--status-pending` (gray), `--status-active` (blue, with pulse), `--status-done` (green).
- Animations: `animate-fade-in`, `animate-scale-in`, custom pulsing dot for "thinking", staggered entrance with delay utility classes.

## File structure
```
src/routes/index.tsx                  # Replace placeholder, mounts <TravelPlannerApp />
src/components/travel/
  TravelPlannerApp.tsx                # Top-level state machine + layout
  Landing.tsx                         # Hero heading + example chips (shown when no messages)
  ChatInput.tsx                       # Sticky bottom input + send button
  MessageBubble.tsx                   # User / AI bubbles
  ThinkingDots.tsx                    # Animated 3-dot indicator
  ClarifyCard.tsx                     # Generic missing-info card (title + option buttons)
  AnswerChip.tsx                      # Small inline confirmation after a card is answered
  AgentPipeline.tsx                   # Vertical list of 7 PipelineStep items
  PipelineStep.tsx                    # Icon + name + status badge + optional inline content
  DateProposalCard.tsx                # 3 date options + Confirm button (Date Optimizer)
  StayProposalCard.tsx                # 3 stay cards (image, price, rating) + Confirm (Stay Agent)
  ItineraryCard.tsx                   # Final styled itinerary (header, day tables, total, reset)
src/lib/travel/mockData.ts            # All scripted content (dates, stays, places, itinerary)
src/lib/travel/types.ts               # Message, PipelineStepState, etc.
```

## State machine (in `TravelPlannerApp`)
Single `phase` enum drives the UI:
1. `landing` — empty messages, show `<Landing />`.
2. `clarifying` — user message sent → 1s thinking → AI summary bubble → cards A→B→C appear sequentially after each answer (0.5s delay).
3. `pipeline` — AI "완벽해요" message → render `<AgentPipeline />`. Steps advance via `setTimeout` (1.5s) and pause for user confirmation at Date Optimizer (step 2) and Stay Agent (step 3).
4. `done` — render `<ItineraryCard />` below pipeline. "일정 다시 짜기" resets to `landing`.

Messages are kept in a single `messages: Message[]` array. Inline interactive cards (clarify cards, date/stay proposals) are rendered as part of the message stream so they scroll naturally with the conversation.

## Pipeline detail
Seven steps, each with status `대기중 | 진행중 | 완료`:
1. 🧠 Orchestrator — instant 완료.
2. 🗓️ Date Optimizer — 진행중, renders `<DateProposalCard />` with 3 date ranges (e.g. 6/20–22, 6/27–29, 6/29–7/1). Confirm → 완료, advance.
3. 🏨 Stay Agent — 진행중, renders `<StayProposalCard />` with 3 바다 전망 stays (generated placeholder images via `imagegen` at build time, price + ★ rating). Confirm → 완료, advance.
4. ⚖️ Budget Balancing — 완료 with one-line text: "숙소 ₩420,000 확정 · 잔여 예산 ₩580,000 (식사·체험·교통)".
5. 📍 Place & Dining — 완료 with a compact list of 6 places; rainy-day items get an "실내" badge (Lucide `CloudRain` + `Home`).
6. 🗺️ Routing Optimizer — 완료 with text "최적 동선 계산 완료 · 총 이동시간 1시간 47분".
7. 📝 Synthesizer — 진행중 (1.5s) → 완료, then `<ItineraryCard />` mounts.

Status badge: small `Badge` with color from semantic tokens; 진행중 uses `animate-pulse` and a spinning Lucide `Loader2`.

## Final itinerary
Header row: `제주도 · 6/27(금)–6/29(일) · 2명 · 총 예산 ₩1,000,000`.
Two day sections (Day 1, Day 2, Day 3), each a table with columns `시간 / 장소 / 활동 / 이동수단 / 예상비용`. 6–7 rows per day with realistic 제주 content (성산일출봉, 협재해변, 흑돼지 맛집, etc.). Footer: 총 예상 비용 ₩978,000 + outline button "일정 다시 짜기" that resets state.

## Mock images
Use `imagegen` (fast tier) to generate 3 stay images saved to `src/assets/` and imported. Prompts: oceanview pension, modern seaside hotel room, quiet hanok-style coastal stay. JPG, ~768×512.

## Design tokens to add
- Three status colors in `:root` (oklch) and mapped under `@theme inline` as `--color-status-pending/active/done`.
- Keep existing palette; no dark mode work needed for the demo.

## Out of scope
- No real chat API, no AI Elements (this is a scripted demo, not an LLM chat — the chat-agent contract's AI SDK requirements don't apply).
- No persistence, no routing beyond `/`, no auth, no Cloud.
- Freeform input after landing simply triggers the same scripted clarifying flow; we don't parse arbitrary user text.