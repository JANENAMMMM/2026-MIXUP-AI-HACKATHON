import { useEffect, useRef, useState } from "react";
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
  Home,
  RotateCcw,
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
  DATE_PROPOSALS,
  STAY_PROPOSALS,
  PLACES,
  ITINERARY,
  TOTAL_COST,
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

export default function TravelPlannerApp() {
  const [phase, setPhase] = useState<Phase>("landing");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [answers, setAnswers] = useState<Answers>({});
  const [activeClarify, setActiveClarify] = useState<ClarifyKey | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<Record<PipelineStepId, StepStatus>>({
    orchestrator: "대기중",
    date: "대기중",
    stay: "대기중",
    budget: "대기중",
    place: "대기중",
    routing: "대기중",
    synth: "대기중",
  });
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, activeClarify, pipelineStatus]);

  const addMessage = (m: Message) => setMessages((prev) => [...prev, m]);

  const startConversation = (text: string) => {
    if (phase !== "landing") return;
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
            text:
              "📋 파악한 정보: **제주도 · 6월 말 · 2박3일**\n아래 정보만 더 알려주시면 바로 시작할게요!",
          }),
      );
      setTimeout(() => {
        addMessage({ id: uid(), role: "clarify", key: "budget" });
        setActiveClarify("budget");
      }, 500);
    }, 1000);
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
        addMessage({
          id: uid(),
          role: "ai",
          text: "✅ 완벽해요! 지금부터 일정을 짜볼게요 🚀",
        });
        setTimeout(startPipeline, 600);
      }, 400);
    }
  };

  const startPipeline = () => {
    setPhase("pipeline");
    addMessage({ id: uid(), role: "pipeline" });
    // Step 1: orchestrator -> instant done
    setTimeout(() => {
      setPipelineStatus((s) => ({ ...s, orchestrator: "완료", date: "진행중" }));
    }, 800);
  };

  const confirmDate = (id: string) => {
    setAnswers((a) => ({ ...a, dateChoice: id }));
    setPipelineStatus((s) => ({ ...s, date: "완료", stay: "진행중" }));
  };

  const confirmStay = (id: string) => {
    setAnswers((a) => ({ ...a, stayChoice: id }));
    setPipelineStatus((s) => ({ ...s, stay: "완료", budget: "진행중" }));
    setTimeout(() => {
      setPipelineStatus((s) => ({ ...s, budget: "완료", place: "진행중" }));
    }, 1500);
    setTimeout(() => {
      setPipelineStatus((s) => ({ ...s, place: "완료", routing: "진행중" }));
    }, 3000);
    setTimeout(() => {
      setPipelineStatus((s) => ({ ...s, routing: "완료", synth: "진행중" }));
    }, 4500);
    setTimeout(() => {
      setPipelineStatus((s) => ({ ...s, synth: "완료" }));
      setPhase("done");
      addMessage({ id: uid(), role: "itinerary" });
    }, 6500);
  };

  const reset = () => {
    setPhase("landing");
    setMessages([]);
    setInput("");
    setAnswers({});
    setActiveClarify(null);
    setPipelineStatus({
      orchestrator: "대기중",
      date: "대기중",
      stay: "대기중",
      budget: "대기중",
      place: "대기중",
      routing: "대기중",
      synth: "대기중",
    });
  };

  const handleSubmit = (text: string) => {
    const t = text.trim();
    if (!t) return;
    setInput("");
    startConversation(t);
  };

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

      <main
        ref={scrollRef}
        className="flex-1 overflow-y-auto"
      >
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
                  answers={answers}
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
            disabled={phase !== "landing"}
          />
          {phase !== "landing" && (
            <p className="mt-2 text-center text-xs text-muted-foreground">
              데모 시연 중입니다 — 위 카드를 눌러 진행해보세요.
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
        placeholder={disabled ? "데모가 진행 중입니다" : "어디로 떠나고 싶으세요? 예) 6월 말 제주도 2박3일…"}
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
  answers,
}: {
  m: Message;
  active: boolean;
  onClarify: (k: ClarifyKey, v: string) => void;
  pipelineStatus: Record<PipelineStepId, StepStatus>;
  onConfirmDate: (id: string) => void;
  onConfirmStay: (id: string) => void;
  onReset: () => void;
  answers: Answers;
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
        <Pipeline
          status={pipelineStatus}
          onConfirmDate={onConfirmDate}
          onConfirmStay={onConfirmStay}
          answers={answers}
        />
      </div>
    );
  }

  if (m.role === "itinerary") {
    return (
      <div className="animate-fade-in">
        <Itinerary onReset={onReset} answers={answers} />
      </div>
    );
  }

  return null;
}

function renderInlineMarkdown(text: string) {
  // very small **bold** parser
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith("**") && p.endsWith("**") ? (
      <strong key={i} className="font-semibold">
        {p.slice(2, -2)}
      </strong>
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
            title: "숙소 분위기는요?",
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

function Pipeline({
  status,
  onConfirmDate,
  onConfirmStay,
  answers,
}: {
  status: Record<PipelineStepId, StepStatus>;
  onConfirmDate: (id: string) => void;
  onConfirmStay: (id: string) => void;
  answers: Answers;
}) {
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
            >
              {s.id === "date" && st === "진행중" && (
                <DateProposalCard onConfirm={onConfirmDate} />
              )}
              {s.id === "date" && st === "완료" && answers.dateChoice && (
                <InlineNote>
                  선택: {DATE_PROPOSALS.find((d) => d.id === answers.dateChoice)?.label}
                </InlineNote>
              )}
              {s.id === "stay" && st === "진행중" && (
                <StayProposalCard onConfirm={onConfirmStay} />
              )}
              {s.id === "stay" && st === "완료" && answers.stayChoice && (
                <InlineNote>
                  선택: {STAY_PROPOSALS.find((x) => x.id === answers.stayChoice)?.name}
                </InlineNote>
              )}
              {s.id === "budget" && st === "완료" && (
                <InlineNote>
                  숙소 ₩420,000 확정 · 잔여 예산 ₩580,000 (식사·체험·교통)
                </InlineNote>
              )}
              {s.id === "place" && st === "완료" && (
                <PlaceList />
              )}
              {s.id === "routing" && st === "완료" && (
                <InlineNote>최적 동선 계산 완료 · 총 이동시간 1시간 47분</InlineNote>
              )}
              {s.id === "synth" && st === "진행중" && (
                <InlineNote>최종 일정표 생성 중…</InlineNote>
              )}
            </PipelineStepRow>
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
        <Check className="h-3 w-3" />
        완료
      </Badge>
    );
  }
  if (status === "진행중") {
    return (
      <Badge className="gap-1 border-transparent bg-status-active text-status-active-foreground hover:bg-status-active animate-pulse">
        <Loader2 className="h-3 w-3 animate-spin" />
        진행중
      </Badge>
    );
  }
  return (
    <Badge variant="secondary" className="bg-status-pending text-status-pending-foreground">
      대기중
    </Badge>
  );
}

function InlineNote({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg bg-muted/60 px-3 py-2 text-sm text-foreground/80 animate-fade-in">
      {children}
    </div>
  );
}

function DateProposalCard({ onConfirm }: { onConfirm: (id: string) => void }) {
  const [selected, setSelected] = useState(DATE_PROPOSALS[1].id);
  return (
    <div className="space-y-2 animate-fade-in">
      <div className="text-xs text-muted-foreground">날짜 3개를 제안합니다. 하나 선택해주세요.</div>
      <div className="grid gap-2">
        {DATE_PROPOSALS.map((d) => (
          <button
            key={d.id}
            onClick={() => setSelected(d.id)}
            className={cn(
              "flex flex-col items-start gap-0.5 rounded-lg border bg-card px-3 py-2 text-left text-sm transition",
              selected === d.id
                ? "border-foreground/60 ring-1 ring-foreground/20"
                : "border-border hover:border-foreground/30",
            )}
          >
            <div className="font-medium">{d.label}</div>
            <div className="text-xs text-muted-foreground">{d.note}</div>
          </button>
        ))}
      </div>
      <Button size="sm" onClick={() => onConfirm(selected)} className="mt-1">
        <Check className="h-3.5 w-3.5" /> 이 날짜로 확정
      </Button>
    </div>
  );
}

function StayProposalCard({ onConfirm }: { onConfirm: (id: string) => void }) {
  const [selected, setSelected] = useState(STAY_PROPOSALS[0].id);
  return (
    <div className="space-y-2 animate-fade-in">
      <div className="text-xs text-muted-foreground">바다 전망 숙소 3곳을 추천합니다.</div>
      <div className="grid gap-2 sm:grid-cols-3">
        {STAY_PROPOSALS.map((s) => (
          <button
            key={s.id}
            onClick={() => setSelected(s.id)}
            className={cn(
              "overflow-hidden rounded-lg border bg-card text-left transition",
              selected === s.id
                ? "border-foreground/60 ring-1 ring-foreground/20"
                : "border-border hover:border-foreground/30",
            )}
          >
            <img
              src={s.image}
              alt={s.name}
              width={768}
              height={512}
              loading="lazy"
              className="h-28 w-full object-cover"
            />
            <div className="p-2.5">
              <div className="text-sm font-medium">{s.name}</div>
              <div className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                <Star className="h-3 w-3 fill-current text-amber-500" />
                {s.rating} · {won(s.price)}/박
              </div>
              <div className="mt-1.5 flex flex-wrap gap-1">
                {s.tags.map((t) => (
                  <span key={t} className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          </button>
        ))}
      </div>
      <Button size="sm" onClick={() => onConfirm(selected)} className="mt-1">
        <Check className="h-3.5 w-3.5" /> 이 숙소로 확정
      </Button>
    </div>
  );
}

function PlaceList() {
  return (
    <div className="space-y-1.5 animate-fade-in">
      <div className="mb-1 flex items-center gap-1.5 text-xs text-muted-foreground">
        <CloudRain className="h-3 w-3" />
        Day 2 오후 비 예보 → 실내 장소 우선 추천
      </div>
      {PLACES.map((p) => (
        <div key={p.name} className="flex items-center justify-between rounded-md bg-muted/40 px-2.5 py-1.5 text-sm">
          <span className="text-foreground/90">
            {p.name} <span className="text-xs text-muted-foreground">· {p.type}</span>
          </span>
          {p.indoor && (
            <span className="inline-flex items-center gap-1 rounded-full bg-status-active px-2 py-0.5 text-[10px] font-medium text-status-active-foreground">
              <Home className="h-2.5 w-2.5" /> 실내
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

/* -------------------- Itinerary -------------------- */

function Itinerary({ onReset, answers }: { onReset: () => void; answers: Answers }) {
  const dateLabel =
    DATE_PROPOSALS.find((d) => d.id === answers.dateChoice)?.label ?? "6/27(금) – 6/29(일)";
  return (
    <Card className="ml-10 gap-0 overflow-hidden p-0 shadow-sm">
      <div className="border-b border-border/60 bg-muted/30 px-5 py-4">
        <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          <FileText className="h-3.5 w-3.5" />
          최종 일정표
        </div>
        <div className="mt-2 text-xl font-semibold tracking-tight">제주도 · 2박3일</div>
        <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-sm text-muted-foreground">
          <span>📅 {dateLabel}</span>
          <span>👥 {answers.people ?? "2명"}</span>
          <span>💰 총 예산 {won(1000000)}</span>
        </div>
      </div>

      <div className="divide-y divide-border/60">
        {ITINERARY.map((d) => (
          <div key={d.day} className="px-5 py-4">
            <div className="mb-3 flex items-baseline gap-2">
              <div className="text-sm font-semibold">{d.day}</div>
              <div className="text-xs text-muted-foreground">{d.date}</div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs font-medium text-muted-foreground">
                    <th className="pb-2 pr-3">시간</th>
                    <th className="pb-2 pr-3">장소</th>
                    <th className="pb-2 pr-3">활동</th>
                    <th className="pb-2 pr-3">이동수단</th>
                    <th className="pb-2 text-right">예상비용</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40">
                  {d.rows.map((r, i) => (
                    <tr key={i}>
                      <td className="py-2 pr-3 text-muted-foreground">{r.time}</td>
                      <td className="py-2 pr-3 font-medium">{r.place}</td>
                      <td className="py-2 pr-3 text-foreground/80">{r.activity}</td>
                      <td className="py-2 pr-3 text-xs text-muted-foreground">{r.transport}</td>
                      <td className="py-2 text-right tabular-nums">
                        {r.cost ? won(r.cost) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border/60 bg-muted/30 px-5 py-4">
        <div>
          <div className="text-xs text-muted-foreground">총 예상 비용</div>
          <div className="text-2xl font-semibold tabular-nums">{won(TOTAL_COST)}</div>
        </div>
        <Button variant="outline" onClick={onReset}>
          <RotateCcw className="h-4 w-4" />
          일정 다시 짜기
        </Button>
      </div>
    </Card>
  );
}