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

const SUGGESTED_QUESTIONS = [
  {
    category: "Pricing",
    question:
      "Which neighbourhoods have the highest average prices for entire homes?",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="12" y1="1" x2="12" y2="23" />
        <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
      </svg>
    ),
  },
  {
    category: "Comparison",
    question:
      "Compare Manhattan vs Brooklyn by price, room type, and reviews.",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <line x1="12" y1="3" x2="12" y2="21" />
      </svg>
    ),
  },
  {
    category: "Features",
    question: "Which features are most common in high-priced listings?",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
      </svg>
    ),
  },
  {
    category: "Reviews",
    question:
      "What review themes appear most often in top-rated listings?",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
  },
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

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <SchemaExplorer schema={schema} />

                <div>
                  <h3 className="text-xs font-semibold text-[var(--color-navy)] mb-2 uppercase tracking-wider">
                    Try a Question
                  </h3>
                  <div className="space-y-1.5">
                    {SUGGESTED_QUESTIONS.map((sq, i) => (
                      <button
                        key={i}
                        onClick={() => handleSend(sq.question)}
                        disabled={loading}
                        className="suggested-question-card group w-full text-left px-3 py-2.5 rounded-xl bg-white border border-[var(--color-border)] hover:border-[var(--color-coral)] hover:shadow-md transition-all duration-200"
                      >
                        <div className="flex items-center gap-1.5 mb-0.5">
                          <span className="text-[var(--color-coral)] opacity-70 group-hover:opacity-100 transition-opacity">
                            {sq.icon}
                          </span>
                          <span className="text-[0.65rem] font-semibold uppercase tracking-wider text-[var(--color-coral)]">
                            {sq.category}
                          </span>
                        </div>
                        <p className="text-[0.8rem] text-[var(--color-navy)] leading-snug">
                          {sq.question}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
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
