"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import Header from "@/components/Header";
import ChatInput from "@/components/ChatInput";
import MessageBubble, {
  type Message,
  type TraceStep,
} from "@/components/MessageBubble";
import WaitingGame from "@/components/WaitingGame";
import PipelineFlowchart from "@/components/PipelineFlowchart";
import DataOverview from "@/components/DataOverview";
import SchemaExplorer from "@/components/SchemaExplorer";
import { getStageForAgent } from "@/lib/pipeline-stages";
import type { TableSchema } from "@/components/SqlQueryBlock";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const WS_BACKEND_URL = BACKEND_URL.replace(/^http/, "ws");

function getStatusFromTraceStep(step: TraceStep): {
  agent: string;
  content: string;
} | null {
  if (step.type === "handoff" && step.target) {
    return {
      agent: step.target,
      content: `Handing work to ${step.target}...`,
    };
  }

  if (step.type === "tool_call") {
    const toolLabel =
      step.tool === "query_database"
        ? "Querying the dataset..."
        : step.tool === "create_visualization"
          ? "Generating visualization..."
          : `Running ${step.tool || "tool"}...`;
    return {
      agent: step.agent || "Agent",
      content: toolLabel,
    };
  }

  if (step.type === "message" && step.agent) {
    return {
      agent: step.agent,
      content: "Preparing response...",
    };
  }

  if (step.type === "agent_start" && step.agent) {
    return {
      agent: step.agent,
      content: `${step.agent} is working...`,
    };
  }

  return null;
}

/* ── SVG icon helpers (keeps the question list compact) ── */
const icons = {
  dollar: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </svg>
  ),
  user: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
    </svg>
  ),
  chat: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  ),
  pin: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z" /><circle cx="12" cy="10" r="3" />
    </svg>
  ),
  calendar: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  ),
  star: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
    </svg>
  ),
  trend: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  ),
  shield: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  ),
  grid: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="12" y1="3" x2="12" y2="21" />
    </svg>
  ),
  clock: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
    </svg>
  ),
  bar: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10" /><line x1="12" y1="20" x2="12" y2="4" /><line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  ),
  home: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  ),
  link: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
    </svg>
  ),
};

const ALL_QUESTIONS = [
  // Row 1 — the showcase questions
  { category: "Pricing",     question: "Which neighbourhoods are the most expensive and why?",                              icon: icons.dollar },
  { category: "Comparison",  question: "Compare Brooklyn and Manhattan listings — pricing, reviews, and host quality",      icon: icons.bar },
  // Row 2
  { category: "Pricing",     question: "How does pricing vary by room type across the five boroughs?",                      icon: icons.dollar },
  { category: "Hosts",       question: "Do superhosts get better review scores than regular hosts?",                        icon: icons.user },
  // Row 3
  { category: "Text",        question: "What words appear most often in negative reviews?",                                 icon: icons.chat },
  { category: "Geographic",  question: "What is the price distribution for listings near Times Square?",                    icon: icons.pin },
  // Row 4
  { category: "Amenities",   question: "Which amenities are most common in top-rated listings?",                            icon: icons.home },
  { category: "Correlation", question: "What is the relationship between listing price and number of reviews?",             icon: icons.link },
  // Row 5
  { category: "Hosts",       question: "What are the top 10 neighbourhoods with the most listings per host?",               icon: icons.user },
  { category: "Trends",      question: "How has host sign-up activity changed over the years?",                             icon: icons.trend },
  // Row 6
  { category: "Quality",     question: "What share of listings in each borough have no reviews?",                           icon: icons.star },
  { category: "Property",    question: "How do accommodation capacity and bedrooms relate to price?",                       icon: icons.home },
  // Row 7
  { category: "Trust",       question: "Are there pricing differences between verified and unverified hosts?",              icon: icons.shield },
  { category: "Availability",question: "What percentage of listings are instantly bookable in each borough?",               icon: icons.calendar },
  // Row 8
  { category: "Policy",      question: "Which boroughs have the longest minimum stay requirements?",                        icon: icons.clock },
  { category: "Text",        question: "What do guests say about cleanliness in Brooklyn reviews?",                         icon: icons.chat },
  // Row 9
  { category: "Market",      question: "Which hosts have the most listings across NYC?",                                    icon: icons.grid },
  { category: "Trends",      question: "How does review activity look month by month over time?",                           icon: icons.trend },
];

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [answered, setAnswered] = useState(false);
  const [schema, setSchema] = useState<Record<string, TableSchema> | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const traceRef = useRef<TraceStep[]>([]);
  const socketRef = useRef<WebSocket | null>(null);
  const [pipelineProgress, setPipelineProgress] = useState<{
    active: string | null;
    completed: Set<string>;
  }>({ active: null, completed: new Set() });

  useEffect(() => {
    fetch(`${BACKEND_URL}/api/schema`)
      .then((res) => res.json())
      .then((data) => setSchema(data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const addMessage = useCallback((msg: Message) => {
    setMessages((prev) => [...prev, msg]);
  }, []);

  const buildFallbackTrace = useCallback(
    (question: string, answer: string, startedAt: number): TraceStep[] => {
      const finishedAt = Date.now() / 1000;

      return [
        {
          type: "agent_start",
          agent: "Orchestrator",
          ts: startedAt,
        },
        {
          type: "message",
          agent: "Orchestrator",
          content: `Submitted your question to the analysis pipeline: "${question}"`,
          ts: startedAt + 0.001,
        },
        {
          type: "message",
          agent: "Orchestrator",
          content:
            "The backend returned a final answer, but it did not include a detailed agent trace for this run.",
          ts: finishedAt,
        },
        {
          type: "message",
          agent: "Orchestrator",
          content: answer,
          ts: finishedAt + 0.001,
        },
      ];
    },
    []
  );

  const handleReset = useCallback(() => {
    setMessages([]);
    setAnswered(false);
    setLoading(false);
    setPipelineProgress({ active: null, completed: new Set() });
    if (socketRef.current) {
      socketRef.current.close();
      socketRef.current = null;
    }
  }, []);

  const handleSend = useCallback(
    async (question: string) => {
      const startedAt = Date.now() / 1000;

      const userMsg: Message = {
        id: Date.now().toString(),
        role: "user",
        content: question,
      };
      addMessage(userMsg);
      setLoading(true);

      const statusId = (Date.now() + 1).toString();
      addMessage({
        id: statusId,
        role: "status",
        content: "Starting analysis pipeline...",
        agent: "Orchestrator",
      });

      traceRef.current = [];

      try {
        if (socketRef.current) {
          socketRef.current.close();
        }

        const socket = new WebSocket(`${WS_BACKEND_URL}/ws/analyze`);
        socketRef.current = socket;

        socket.onopen = () => {
          socket.send(JSON.stringify({ question, history: [] }));
        };

        socket.onmessage = (event) => {
          const payload = JSON.parse(event.data);

          if (payload.type === "heartbeat") return;

          if (payload.type === "status") {
            setMessages((prev) =>
              prev.map((message) =>
                message.id === statusId
                  ? {
                      ...message,
                      content: payload.content || message.content,
                      agent: payload.agent || message.agent,
                    }
                  : message
              )
            );
            return;
          }

          if (payload.type === "trace" && payload.step) {
            traceRef.current = [...traceRef.current, payload.step as TraceStep];

            // Update pipeline flowchart progress
            const step = payload.step as TraceStep;
            if (step.type === "agent_start" || step.type === "handoff") {
              const agentName = step.agent || step.target;
              if (agentName) {
                const matchedStage = getStageForAgent(agentName);
                if (matchedStage) {
                  setPipelineProgress((prev) => {
                    const newCompleted = new Set(prev.completed);
                    if (prev.active && prev.active !== matchedStage.key) {
                      newCompleted.add(prev.active);
                    }
                    return { active: matchedStage.key, completed: newCompleted };
                  });
                }
              }
            }

            const statusUpdate = getStatusFromTraceStep(payload.step as TraceStep);
            if (statusUpdate) {
              setMessages((prev) =>
                prev.map((message) =>
                  message.id === statusId
                    ? {
                        ...message,
                        content: statusUpdate.content,
                        agent: statusUpdate.agent,
                      }
                    : message
                )
              );
            }
            return;
          }

          if (payload.type === "result") {
            setMessages((prev) => prev.filter((m) => m.id !== statusId));
            const trace =
              traceRef.current.length > 0
                ? traceRef.current
                : buildFallbackTrace(question, payload.content, startedAt);

            addMessage({
              id: (Date.now() + 2).toString(),
              role: "assistant",
              content: payload.content,
              artifacts: payload.artifacts,
              trace,
            });
            setLoading(false);
            setAnswered(true);
            setPipelineProgress({ active: null, completed: new Set() });
            socket.close();
            return;
          }

          if (payload.type === "error") {
            setMessages((prev) => prev.filter((m) => m.id !== statusId));
            addMessage({
              id: (Date.now() + 2).toString(),
              role: "assistant",
              content: `**Error:** ${payload.content || "Something went wrong"}`,
            });
            setLoading(false);
            setAnswered(true);
            setPipelineProgress({ active: null, completed: new Set() });
            socket.close();
          }
        };

        socket.onerror = () => {
          setMessages((prev) => prev.filter((m) => m.id !== statusId));
          addMessage({
            id: (Date.now() + 2).toString(),
            role: "assistant",
            content: `**Connection error:** Could not reach the backend. Make sure the server is running at ${BACKEND_URL}`,
          });
          setLoading(false);
        };

        socket.onclose = () => {
          socketRef.current = null;
        };
      } catch {
        setMessages((prev) => prev.filter((m) => m.id !== statusId));
        addMessage({
          id: (Date.now() + 2).toString(),
          role: "assistant",
          content: `**Connection error:** Could not reach the backend. Make sure the server is running at ${BACKEND_URL}`,
        });
        setLoading(false);
      }
    },
    [addMessage, buildFallbackTrace]
  );

  const userQuestion = messages.find((m) => m.role === "user")?.content;

  return (
    <div className="flex flex-col h-screen">
      <Header answered={answered} onReset={handleReset} />

      <main className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="max-w-4xl mx-auto px-6 py-4">
          {messages.length === 0 ? (
            <div className="landing-content">
              <DataOverview schema={schema} />

              {/* ── Suggested questions — the hero section ── */}
              <div className="mb-4">
                <h3 className="text-xs font-semibold text-[var(--color-navy)] mb-2.5 uppercase tracking-wider">
                  Try a Question
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {ALL_QUESTIONS.map((sq, i) => (
                    <button
                      key={i}
                      onClick={() => handleSend(sq.question)}
                      disabled={loading}
                      className="suggested-question-card group w-full text-left px-3 py-2 rounded-xl bg-white border border-[var(--color-border)] hover:border-[var(--color-coral)] hover:shadow-md transition-all duration-200"
                    >
                      <div className="flex items-start gap-2">
                        <span className="text-[var(--color-coral)] opacity-60 group-hover:opacity-100 transition-opacity mt-0.5 shrink-0">
                          {sq.icon}
                        </span>
                        <div className="min-w-0">
                          <span className="text-[0.6rem] font-semibold uppercase tracking-wider text-[var(--color-coral)]">
                            {sq.category}
                          </span>
                          <p className="text-[0.78rem] text-[var(--color-navy)] leading-snug">
                            {sq.question}
                          </p>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* ── Schema explorer — compact, below questions ── */}
              <SchemaExplorer schema={schema} />
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  schema={schema}
                  userQuestion={userQuestion}
                />
              ))}
            </div>
          )}
          {loading && <WaitingGame />}
          <div ref={bottomRef} />
        </div>
      </main>

      {loading && (
        <PipelineFlowchart
          activeStage={pipelineProgress.active}
          completedStages={pipelineProgress.completed}
        />
      )}

      {!answered && (
        <footer className="border-t border-[var(--color-border)] bg-white/80 backdrop-blur-md">
          <div className="max-w-4xl mx-auto px-6 py-4">
            <ChatInput onSend={handleSend} disabled={loading} />
          </div>
        </footer>
      )}
    </div>
  );
}
