import { useEffect, useRef, useState } from "react";
import { startPlan, resumePlan } from "@/lib/api";
import MarkdownContent from "./MarkdownContent";
import type { PlanResult, DateCandidate, HotelCandidate } from "@/lib/api";
import {
  Send,
  Sparkles,
  Brain,
  CalendarDays,
  Hotel,
  Scale,
  MapPin,
  Route,
  FileText,
  Loader2,
  Check,
  Star,
  CloudRain,
  RotateCcw,
  Plane,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import {
  EXAMPLE_PROMPTS,
  BUDGET_OPTIONS,
  PEOPLE_OPTIONS,
  STAY_OPTIONS,
  won,
} from "@/lib/travel/mockData";
import type {
  Answers,
  ClarifyKey,
  Message,
  Phase,
  PipelineStepId,
  StepStatus,
} from "@/lib/travel/types";

const uid = () => Math.random().toString(36).slice(2, 10);

const CLARIFY_ORDER: ClarifyKey[] = ["budget", "people", "stay"];

const PIPELINE_STEPS: { id: PipelineStepId; icon: typeof Brain; name: string }[] = [
  { id: "orchestrator", icon: Brain, name: "Orchestrator" },
  { id: "date", icon: CalendarDays, name: "Date Optimizer" },
  { id: "stay", icon: Hotel, name: "Stay Agent" },
  { id: "budget", icon: Scale, name: "Budget Balancing" },
  { id: "place", icon: MapPin, name: "Place & Dining" },
  { id: "routing", icon: Route, name: "Routing Optimizer" },
  { id: "synth", icon: FileText, name: "Synthesizer" },
];

const INITIAL_PIPELINE: Record<PipelineStepId, StepStatus> = {
  orchestrator: "대기중",
  date: "대기중",
  stay: "대기중",
  budget: "대기중",
  place: "대기중",
  routing: "대기중",
  synth: "대기중",
};

export default function TravelPlannerApp() {
  const [phase, setPhase] = useState<Phase>("landing");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [answers, setAnswers] = useState<Answers>({});
  const [activeClarify, setActiveClarify] = useState<ClarifyKey | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<Record<PipelineStepId, StepStatus>>(INITIAL_PIPELINE);
  const [planResult, setPlanResult] = useState<PlanResult | null>(null);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const userQueryRef = useRef<string>("");

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, activeClarify, pipelineStatus]);

  const addMessage = (m: Message) => setMessages((prev) => [...prev, m]);

  const startConversation = (text: string) => {
    if (phase !== "landing") return;
    userQueryRef.current = text;
    setPhase("clarifying");
    addMessage({ id: uid(), role: "user", text });
    const thinkingId = uid();
    addMessage({ id: thinkingId, role: "ai-thinking" });
    setTimeout(() => {
      setMessages((prev) =>
        prev
          .filter((m) => m.id !== thinkingId)
          .concat({
            id: uid(),
            role: "ai",
            text: "📋 요청을 파악했어요! 아래 정보를 알려주시면 최적 일정을 설계할게요.",
          }),
      );
      setTimeout(() => {
        addMessage({ id: uid(), role: "clarify", key: "budget" });
        setActiveClarify("budget");
      }, 500);
    }, 800);
  };

  const answerClarify = (key: ClarifyKey, value: string) => {
    setAnswers((a) => ({ ...a, [key]: value }));
    setMessages((prev) =>
      prev
        .filter((m) => !(m.role === "clarify" && m.key === key))
        .concat({ id: uid(), role: "answer", text: `${labelFor(key)}: ${value}` }),
    );
    const next = CLARIFY_ORDER[CLARIFY_ORDER.indexOf(key) + 1];
    if (next) {
      setActiveClarify(null);
      setTimeout(() => {
        addMessage({ id: uid(), role: "clarify", key: next });
        setActiveClarify(next);
      }, 500);
    } else {
      setActiveClarify(null);
      setTimeout(() => {
        addMessage({ id: uid(), role: "ai", text: "✅ 완벽해요! 지금부터 일정을 짜볼게요 🚀" });
        setTimeout(callStartPlan, 600);
      }, 400);
    }
  };

  const callStartPlan = async () => {
    setPhase("loading");
    setError(null);
    addMessage({ id: uid(), role: "pipeline" });

    // 파이프라인 애니메이션 (orchestrator 시작)
    setPipelineStatus((s) => ({ ...s, orchestrator: "진행중" }));

    try {
      const currentAnswers = answers; // 클로저 캡처
      const res = await startPlan({
        message: userQueryRef.current,
        budget: currentAnswers.budget,
        people: currentAnswers.people,
        stay: currentAnswers.stay,
      });

      handlePlanResult(res.thread_id, res.phase, res.candidates, res.result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "API 오류가 발생했습니다.");
      setPhase("done");
    }
  };

  const handlePlanResult = (
    tid: string,
    resultPhase: string,
    candidates?: DateCandidate[] | HotelCandidate[],
    result?: PlanResult,
  ) => {
    setThreadId(tid);

    if (resultPhase === "date_selection") {
      setPipelineStatus((s) => ({ ...s, orchestrator: "완료", date: "진행중" }));
      setPhase("date_selection");
      addMessage({
        id: uid(),
        role: "date_proposal",
        question: "날짜를 선택해주세요:",
        candidates: (candidates ?? []) as DateCandidate[],
      });
    } else if (resultPhase === "hotel_selection") {
      setPipelineStatus((s) => ({
        ...s,
        orchestrator: "완료",
        date: "완료",
        stay: "진행중",
      }));
      setPhase("hotel_selection");
      addMessage({
        id: uid(),
        role: "hotel_proposal",
        question: "숙소를 선택해주세요:",
        candidates: (candidates ?? []) as HotelCandidate[],
      });
    } else if (resultPhase === "done" && result) {
      setPipelineStatus({
        orchestrator: "완료",
        date: "완료",
        stay: "완료",
        budget: "완료",
        place: "완료",
        routing: "완료",
        synth: "완료",
      });
      setPlanResult(result);
      setPhase("done");
      addMessage({ id: uid(), role: "itinerary" });
    }
  };

  const confirmDate = async (choice: string) => {
    if (!threadId) return;
    setMessages((prev) => prev.filter((m) => m.role !== "date_proposal"));
    addMessage({ id: uid(), role: "answer", text: `날짜 선택: ${choice}번` });
    setPipelineStatus((s) => ({ ...s, date: "완료", stay: "진행중" }));
    setPhase("resuming");

    try {
      const res = await resumePlan(threadId, choice);
      handlePlanResult(res.thread_id, res.phase, res.candidates, res.result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "API 오류가 발생했습니다.");
      setPhase("done");
    }
  };

  const confirmStay = async (choice: string) => {
    if (!threadId) return;
    setMessages((prev) => prev.filter((m) => m.role !== "hotel_proposal"));
    addMessage({ id: uid(), role: "answer", text: `숙소 선택: ${choice}번` });
    setPipelineStatus((s) => ({ ...s, stay: "완료", budget: "진행중" }));
    setPhase("resuming");

    try {
      const res = await resumePlan(threadId, choice);

      // budget → place → routing → synth 애니메이션
      setTimeout(() => setPipelineStatus((s) => ({ ...s, budget: "완료", place: "진행중" })), 800);
      setTimeout(() => setPipelineStatus((s) => ({ ...s, place: "완료", routing: "진행중" })), 2000);
      setTimeout(() => setPipelineStatus((s) => ({ ...s, routing: "완료", synth: "진행중" })), 3200);

      handlePlanResult(res.thread_id, res.phase, res.candidates, res.result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "API 오류가 발생했습니다.");
      setPhase("done");
    }
  };

  const reset = () => {
    setPlanResult(null);
    setPhase("landing");
    setMessages([]);
    setInput("");
    setAnswers({});
    setActiveClarify(null);
    setThreadId(null);
    setError(null);
    setPipelineStatus(INITIAL_PIPELINE);
  };

  const handleSubmit = (text: string) => {
    const t = text.trim();
    if (!t) return;
    setInput("");
    startConversation(t);
  };

  const isInputDisabled = phase !== "landing";

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="border-b border-border/60 bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-[800px] items-center gap-2 px-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-foreground text-background">
            <Sparkles className="h-4 w-4" />
          </div>
          <div className="text-sm font-semibold tracking-tight">AI 여행 플래너</div>
        </div>
      </header>

      <main ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-[800px] px-4 pb-40 pt-8">
          {phase === "landing" ? (
            <Landing onPick={handleSubmit} />
          ) : (
            <div className="flex flex-col gap-4">
              {messages.map((m) => (
                <MessageRow
                  key={m.id}
                  m={m}
                  active={m.role === "clarify" && activeClarify === m.key}
                  onClarify={answerClarify}
                  pipelineStatus={pipelineStatus}
                  onConfirmDate={confirmDate}
                  onConfirmStay={confirmStay}
                  onReset={reset}
                  planResult={planResult}
                  error={error}
                />
              ))}
            </div>
          )}
        </div>
      </main>

      <div className="fixed bottom-0 left-0 right-0 border-t border-border/60 bg-background/95 backdrop-blur">
        <div className="mx-auto w-full max-w-[800px] px-4 py-4">
          <ChatInput
            value={input}
            onChange={setInput}
            onSubmit={() => handleSubmit(input)}
            disabled={isInputDisabled}
          />
          {isInputDisabled && (
            <p className="mt-2 text-center text-xs text-muted-foreground">
              {phase === "loading" || phase === "resuming"
                ? "AI가 분석 중입니다…"
                : "카드를 선택해 진행해주세요."}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function labelFor(key: ClarifyKey) {
  return key === "budget" ? "예산" : key === "people" ? "인원" : "숙소";
}

/* -------------------- Landing -------------------- */

function Landing({ onPick }: { onPick: (text: string) => void }) {
  return (
    <div className="flex min-h-[calc(100vh-14rem)] flex-col items-center justify-center text-center animate-fade-in">
      <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">AI 여행 플래너</h1>
      <p className="mt-3 text-base text-muted-foreground sm:text-lg">
        어디든, 언제든 — 그냥 말해주세요
      </p>
      <div className="mt-10 flex flex-wrap items-center justify-center gap-2">
        {EXAMPLE_PROMPTS.map((p) => (
          <button
            key={p}
            onClick={() => onPick(p)}
            className="rounded-full border border-border bg-card px-4 py-2 text-sm text-foreground/80 shadow-sm transition hover:border-foreground/30 hover:bg-accent hover:text-foreground"
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}

/* -------------------- Chat input -------------------- */

function ChatInput({
  value,
  onChange,
  onSubmit,
  disabled,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
}) {
  return (
    <div className="relative">
      <Textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            onSubmit();
          }
        }}
        placeholder={disabled ? "AI가 진행 중입니다" : "어디로 떠나고 싶으세요? 예) 6월 말 제주도 2박3일…"}
        rows={2}
        disabled={disabled}
        className="min-h-[60px] resize-none rounded-2xl border-border bg-card px-4 py-3 pr-14 text-base shadow-sm focus-visible:ring-2 focus-visible:ring-ring"
      />
      <Button
        type="button"
        size="icon"
        onClick={onSubmit}
        disabled={disabled || !value.trim()}
        className="absolute bottom-3 right-3 h-9 w-9 rounded-full"
        aria-label="보내기"
      >
        <Send className="h-4 w-4" />
      </Button>
    </div>
  );
}

/* -------------------- Message row -------------------- */

function MessageRow({
  m,
  active,
  onClarify,
  pipelineStatus,
  onConfirmDate,
  onConfirmStay,
  onReset,
  planResult,
  error,
}: {
  m: Message;
  active: boolean;
  onClarify: (k: ClarifyKey, v: string) => void;
  pipelineStatus: Record<PipelineStepId, StepStatus>;
  onConfirmDate: (choice: string) => void;
  onConfirmStay: (choice: string) => void;
  onReset: () => void;
  planResult: PlanResult | null;
  error: string | null;
}) {
  if (m.role === "user") {
    return (
      <div className="flex justify-end animate-fade-in">
        <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-chat-user px-4 py-2.5 text-sm text-chat-user-foreground shadow-sm">
          {m.text}
        </div>
      </div>
    );
  }

  if (m.role === "ai") {
    return (
      <div className="flex animate-fade-in items-start gap-3">
        <AiAvatar />
        <div className="max-w-[85%] whitespace-pre-wrap text-sm leading-relaxed text-foreground">
          {renderInlineMarkdown(m.text)}
        </div>
      </div>
    );
  }

  if (m.role === "ai-thinking") {
    return (
      <div className="flex animate-fade-in items-start gap-3">
        <AiAvatar />
        <ThinkingDots />
      </div>
    );
  }

  if (m.role === "answer") {
    return (
      <div className="flex justify-end animate-fade-in">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-status-done px-3 py-1 text-xs font-medium text-status-done-foreground">
          <Check className="h-3 w-3" />
          {m.text}
        </span>
      </div>
    );
  }

  if (m.role === "clarify") {
    return (
      <div className="animate-fade-in">
        <ClarifyCard k={m.key} disabled={!active} onAnswer={onClarify} />
      </div>
    );
  }

  if (m.role === "pipeline") {
    return (
      <div className="animate-fade-in">
        <Pipeline status={pipelineStatus} />
      </div>
    );
  }

  if (m.role === "date_proposal") {
    return (
      <div className="animate-fade-in">
        <DateProposalCard
          question={m.question}
          candidates={m.candidates}
          onConfirm={onConfirmDate}
        />
      </div>
    );
  }

  if (m.role === "hotel_proposal") {
    return (
      <div className="animate-fade-in">
        <HotelProposalCard
          question={m.question}
          candidates={m.candidates}
          onConfirm={onConfirmStay}
        />
      </div>
    );
  }

  if (m.role === "itinerary") {
    return (
      <div className="animate-fade-in">
        <Itinerary onReset={onReset} planResult={planResult} error={error} />
      </div>
    );
  }

  return null;
}

function renderInlineMarkdown(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith("**") && p.endsWith("**") ? (
      <strong key={i} className="font-semibold">{p.slice(2, -2)}</strong>
    ) : (
      <span key={i}>{p}</span>
    ),
  );
}

function AiAvatar() {
  return (
    <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-foreground text-background">
      <Sparkles className="h-3.5 w-3.5" />
    </div>
  );
}

function ThinkingDots() {
  return (
    <div className="flex items-center gap-1 rounded-2xl bg-muted px-3 py-2.5">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:-0.3s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:-0.15s]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/60" />
    </div>
  );
}

/* -------------------- Clarify card -------------------- */

function ClarifyCard({
  k,
  disabled,
  onAnswer,
}: {
  k: ClarifyKey;
  disabled: boolean;
  onAnswer: (k: ClarifyKey, v: string) => void;
}) {
  const config =
    k === "budget"
      ? { emoji: "💰", title: "여행 예산이 어느 정도예요?", options: BUDGET_OPTIONS.map((o) => ({ label: o })) }
      : k === "people"
        ? { emoji: "👥", title: "몇 명이서 가세요?", options: PEOPLE_OPTIONS.map((o) => ({ label: o })) }
        : {
            emoji: "🏨",
            title: "숙소 분위기는요? (특정 호텔명도 입력 가능해요)",
            options: STAY_OPTIONS.map((o) => ({ label: `${o.emoji} ${o.label}`, value: o.label })),
          };
  return (
    <Card className={cn("ml-10 max-w-[85%] gap-3 p-4 shadow-sm animate-scale-in", disabled && "opacity-60")}>
      <div className="text-sm font-medium">
        <span className="mr-1.5">{config.emoji}</span>
        {config.title}
      </div>
      <div className="flex flex-wrap gap-2">
        {config.options.map((o) => {
          const value: string = (o as { value?: string }).value ?? o.label;
          return (
            <Button
              key={o.label}
              variant="outline"
              size="sm"
              disabled={disabled}
              onClick={() => onAnswer(k, value)}
              className="rounded-full"
            >
              {o.label}
            </Button>
          );
        })}
      </div>
    </Card>
  );
}

/* -------------------- Pipeline -------------------- */

function Pipeline({ status }: { status: Record<PipelineStepId, StepStatus> }) {
  return (
    <Card className="ml-10 gap-0 p-0 shadow-sm">
      <div className="border-b border-border/60 px-4 py-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">
        Agent Pipeline
      </div>
      <ol className="divide-y divide-border/60">
        {PIPELINE_STEPS.map((s, idx) => {
          const st = status[s.id];
          const visible = st !== "대기중" || (idx > 0 && status[PIPELINE_STEPS[idx - 1].id] !== "대기중");
          return (
            <PipelineStepRow
              key={s.id}
              icon={<s.icon className="h-4 w-4" />}
              name={s.name}
              status={st}
              visible={visible}
            />
          );
        })}
      </ol>
    </Card>
  );
}

function PipelineStepRow({
  icon,
  name,
  status,
  visible,
  children,
}: {
  icon: React.ReactNode;
  name: string;
  status: StepStatus;
  visible: boolean;
  children?: React.ReactNode;
}) {
  return (
    <li className={cn("px-4 py-3 transition-opacity", visible ? "opacity-100" : "opacity-40")}>
      <div className="flex items-center gap-3">
        <div
          className={cn(
            "flex h-8 w-8 items-center justify-center rounded-lg",
            status === "완료"
              ? "bg-status-done text-status-done-foreground"
              : status === "진행중"
                ? "bg-status-active text-status-active-foreground"
                : "bg-status-pending text-status-pending-foreground",
          )}
        >
          {icon}
        </div>
        <div className="flex-1 text-sm font-medium">{name}</div>
        <StatusBadge status={status} />
      </div>
      {children && <div className="mt-3 pl-11">{children}</div>}
    </li>
  );
}

function StatusBadge({ status }: { status: StepStatus }) {
  if (status === "완료") {
    return (
      <Badge className="gap-1 border-transparent bg-status-done text-status-done-foreground hover:bg-status-done">
        <Check className="h-3 w-3" />완료
      </Badge>
    );
  }
  if (status === "진행중") {
    return (
      <Badge className="gap-1 border-transparent bg-status-active text-status-active-foreground hover:bg-status-active animate-pulse">
        <Loader2 className="h-3 w-3 animate-spin" />진행중
      </Badge>
    );
  }
  return (
    <Badge variant="secondary" className="bg-status-pending text-status-pending-foreground">
      대기중
    </Badge>
  );
}

/* -------------------- Date Proposal -------------------- */

function DateProposalCard({
  question,
  candidates,
  onConfirm,
}: {
  question: string;
  candidates: DateCandidate[];
  onConfirm: (choice: string) => void;
}) {
  const [selected, setSelected] = useState("1");

  return (
    <Card className="ml-10 max-w-[85%] gap-3 p-4 shadow-sm animate-scale-in">
      <div className="flex items-center gap-2 text-sm font-medium">
        <CalendarDays className="h-4 w-4 text-muted-foreground" />
        {question}
      </div>
      <div className="grid gap-2">
        {candidates.map((c, i) => {
          const idx = String(i + 1);
          const stopsLabel =
            c.stops === 0 ? "직항" : c.stops != null && c.stops > 0 ? `경유 ${c.stops}회` : "";
          return (
            <button
              key={idx}
              onClick={() => setSelected(idx)}
              className={cn(
                "flex flex-col items-start gap-1 rounded-lg border bg-card px-3 py-2.5 text-left text-sm transition",
                selected === idx
                  ? "border-foreground/60 ring-1 ring-foreground/20"
                  : "border-border hover:border-foreground/30",
              )}
            >
              <div className="flex items-center gap-2 font-medium">
                <span>{c.check_in} ~ {c.check_out}</span>
                {i === 0 && (
                  <span className="rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">
                    추천
                  </span>
                )}
              </div>
              <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
                <span>{c.weather_summary}</span>
                {c.flight_price > 0 && (
                  <span className="flex items-center gap-1">
                    <Plane className="h-3 w-3" />
                    {won(c.flight_price)}
                    {stopsLabel && ` · ${stopsLabel}`}
                    {c.airline_name && ` · ${c.airline_name}`}
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>
      <Button size="sm" onClick={() => onConfirm(selected)} className="mt-1">
        <Check className="h-3.5 w-3.5" /> 이 날짜로 확정
      </Button>
    </Card>
  );
}

/* -------------------- Hotel Proposal -------------------- */

function HotelProposalCard({
  question,
  candidates,
  onConfirm,
}: {
  question: string;
  candidates: HotelCandidate[];
  onConfirm: (choice: string) => void;
}) {
  const [selected, setSelected] = useState("1");

  return (
    <Card className="ml-10 max-w-[90%] gap-3 p-4 shadow-sm animate-scale-in">
      <div className="flex items-center gap-2 text-sm font-medium">
        <Hotel className="h-4 w-4 text-muted-foreground" />
        {question}
      </div>
      <div className="grid gap-3">
        {candidates.map((h, i) => {
          const idx = String(i + 1);
          const isSelected = selected === idx;
          return (
            <button
              key={idx}
              onClick={() => setSelected(idx)}
              className={cn(
                "flex flex-col items-start gap-2 rounded-lg border bg-card p-3 text-left transition",
                isSelected
                  ? "border-foreground/60 ring-1 ring-foreground/20"
                  : "border-border hover:border-foreground/30",
              )}
            >
              {/* 헤더 행 */}
              <div className="flex w-full items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className={cn(
                    "flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold",
                    isSelected ? "bg-foreground text-background" : "bg-muted text-muted-foreground",
                  )}>
                    {idx}
                  </span>
                  <span className="text-sm font-semibold leading-tight">{h.name}</span>
                </div>
                <div className="shrink-0 text-right">
                  {h.cost > 0 && (
                    <div className="text-sm font-semibold tabular-nums">{won(h.cost)}</div>
                  )}
                  {h.rating > 0 && (
                    <div className="flex items-center justify-end gap-0.5 text-xs text-muted-foreground">
                      <Star className="h-3 w-3 fill-current text-amber-500" />
                      {h.rating}
                    </div>
                  )}
                </div>
              </div>

              {/* 주소 */}
              {h.address && (
                <div className="flex items-start gap-1 text-xs text-muted-foreground">
                  <MapPin className="mt-0.5 h-3 w-3 shrink-0" />
                  <span className="line-clamp-1">{h.address}</span>
                </div>
              )}

              {/* 설명 */}
              {h.description && (
                <p className="text-xs text-foreground/80 leading-relaxed line-clamp-2">
                  {h.description}
                </p>
              )}

              {/* 편의시설 태그 */}
              {h.amenities?.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {h.amenities.map((a) => (
                    <span
                      key={a}
                      className="rounded-full bg-muted px-2 py-0.5 text-[10px] text-muted-foreground"
                    >
                      {a}
                    </span>
                  ))}
                </div>
              )}

              {/* 상세 링크 */}
              {h.details_link && h.details_link !== "https://example.com/mock1"
                && h.details_link !== "https://example.com/mock2"
                && h.details_link !== "https://example.com/mock3" && (
                <a
                  href={h.details_link}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="text-[11px] text-primary underline underline-offset-2 hover:opacity-80"
                >
                  상세 정보 보기 →
                </a>
              )}
            </button>
          );
        })}
      </div>
      <Button size="sm" onClick={() => onConfirm(selected)} className="mt-1">
        <Check className="h-3.5 w-3.5" /> 이 숙소로 확정
      </Button>
    </Card>
  );
}

/* -------------------- Itinerary -------------------- */

function Itinerary({
  onReset,
  planResult,
  error,
}: {
  onReset: () => void;
  planResult: PlanResult | null;
  error: string | null;
}) {
  if (error) {
    return (
      <Card className="ml-10 gap-0 overflow-hidden p-0 shadow-sm">
        <div className="px-5 py-6 text-center">
          <p className="text-sm font-medium text-destructive">오류가 발생했습니다</p>
          <p className="mt-1 text-xs text-muted-foreground">{error}</p>
        </div>
        <div className="flex justify-end border-t border-border/60 bg-muted/30 px-5 py-4">
          <Button variant="outline" onClick={onReset}>
            <RotateCcw className="h-4 w-4" /> 다시 시도
          </Button>
        </div>
      </Card>
    );
  }

  if (!planResult?.final_report) {
    return (
      <Card className="ml-10 gap-0 p-6 shadow-sm text-center">
        <p className="text-sm text-muted-foreground">결과를 불러오는 중입니다…</p>
      </Card>
    );
  }

  return (
    <Card className="ml-10 gap-0 overflow-hidden p-0 shadow-sm">
      <div className="border-b border-border/60 bg-muted/30 px-5 py-4">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          <FileText className="h-3.5 w-3.5" />
          최종 일정표
        </div>
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
          {planResult.hotel_name && <span>🏨 {planResult.hotel_name}</span>}
          {planResult.hotel_cost > 0 && <span>💰 숙박 {won(planResult.hotel_cost)}</span>}
          {planResult.remaining_budget > 0 && <span>잔여 {won(planResult.remaining_budget)}</span>}
        </div>
        {planResult.weather_summary && (
          <div className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
            <CloudRain className="h-3 w-3" />
            {planResult.weather_summary.split("\n")[0]}
          </div>
        )}
      </div>
      <div className="px-5 py-4">
        <MarkdownContent>{planResult.final_report}</MarkdownContent>
      </div>
      <div className="flex justify-end border-t border-border/60 bg-muted/30 px-5 py-4">
        <Button variant="outline" onClick={onReset}>
          <RotateCcw className="h-4 w-4" /> 일정 다시 짜기
        </Button>
      </div>
    </Card>
  );
}
