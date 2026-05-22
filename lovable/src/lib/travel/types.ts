export type Phase = "landing" | "clarifying" | "pipeline" | "done";

export type ClarifyKey = "budget" | "people" | "stay";

export type Message =
  | { id: string; role: "user"; text: string }
  | { id: string; role: "ai"; text: string }
  | { id: string; role: "ai-thinking" }
  | { id: string; role: "clarify"; key: ClarifyKey }
  | { id: string; role: "answer"; text: string }
  | { id: string; role: "pipeline" }
  | { id: string; role: "itinerary" };

export type StepStatus = "대기중" | "진행중" | "완료";

export type PipelineStepId =
  | "orchestrator"
  | "date"
  | "stay"
  | "budget"
  | "place"
  | "routing"
  | "synth";

export type Answers = {
  budget?: string;
  people?: string;
  stay?: string;
  dateChoice?: string;
  stayChoice?: string;
};