"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import Header from "@/components/Header";
import ChatInput from "@/components/ChatInput";
import DataOverview from "@/components/DataOverview";
import MessageBubble, {
  type Message,
  type TraceStep,
} from "@/components/MessageBubble";
import WaitingGame from "@/components/WaitingGame";
import PipelineFlowchart from "@/components/PipelineFlowchart";
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

const QUESTION_GROUPS = [
  {
    title: "Pricing & Geography",
    description: "Explore where prices move and which neighbourhoods stand out.",
    questions: [
      "Which neighbourhoods have the highest average prices for entire homes?",
      "How does price vary by room type across the five boroughs?",
      "Which Manhattan neighbourhoods stand out on both price and review scores?",
      "How do accommodates and bedrooms relate to listing price?",
    ],
  },
  {
    title: "Hosts & Quality",
    description: "Look at host behavior, listing quality, and operational signals.",
    questions: [
      "Do superhosts get better review scores than other hosts?",
      "Which amenities are most common in top-rated listings?",
      "How do prices differ between hosts with verified identity and those without?",
      "What percentage of listings are instantly bookable in each borough?",
    ],
  },
  {
    title: "Reviews & Sentiment",
    description: "Use guest feedback to surface patterns in experience and demand.",
    questions: [
      "What words appear most often in reviews for low-rated listings?",
      "What do guests say about cleanliness in Brooklyn reviews?",
      "How does review activity change month by month?",
      "Which borough has the highest share of listings with no reviews?",
    ],
  },
  {
    title: "Supply & Market Structure",
    description: "Understand inventory, concentration, and how hosts shape the market.",
    questions: [
      "Compare Brooklyn and Manhattan on price, reviews, and host quality.",
      "Which neighbourhoods have the highest host concentration?",
      "How has host sign-up activity changed over the years?",
      "Which hosts manage the most listings across NYC?",
      "Which boroughs have the longest minimum stay requirements?",
    ],
  },
];

function buildConversationHistory(messages: Message[]) {
  return messages
    .filter(
      (message): message is Message =>
        (message.role === "user" || message.role === "assistant") &&
        typeof message.content === "string" &&
        message.content.trim().length > 0
    )
    .map((message) => ({
      role: message.role,
      content: message.content,
    }));
}

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

  // Auto-scroll only for user messages (so the user sees their own question),
  // not when the assistant response arrives (let them read from the top).
  const lastMessageRef = useRef<string | null>(null);
  useEffect(() => {
    const last = messages[messages.length - 1];
    if (last && last.id !== lastMessageRef.current && last.role === "user") {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
    if (last) lastMessageRef.current = last.id;
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
      const history = buildConversationHistory(messages);

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
          socket.send(JSON.stringify({ question, history }));
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
              question,
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
    [addMessage, buildFallbackTrace, messages]
  );

  return (
    <div className="flex flex-col h-screen">
      <Header answered={answered} onReset={handleReset} />

      <main className="flex-1 overflow-y-auto scrollbar-thin">
        {messages.length === 0 ? (
          <div className="min-h-full px-6 py-8 sm:py-10 lg:py-12">
            <div className="w-full max-w-4xl mx-auto landing-content">
              <DataOverview schema={schema} />

              <p className="text-xs font-semibold text-[var(--color-gray-warm)] uppercase tracking-[0.18em] text-center mb-3 sm:mb-4">
                Explore By Topic
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {QUESTION_GROUPS.map((group) => (
                  <section
                    key={group.title}
                    className="rounded-2xl border border-[var(--color-border)] bg-white/95 px-4 py-4 shadow-sm"
                  >
                    <div className="mb-3">
                      <h3 className="text-sm font-semibold text-[var(--color-navy)]">
                        {group.title}
                      </h3>
                      <p className="mt-1 text-[0.78rem] leading-relaxed text-[var(--color-gray-warm)]">
                        {group.description}
                      </p>
                    </div>

                    <div className="space-y-2">
                      {group.questions.map((q) => (
                        <button
                          key={q}
                          onClick={() => handleSend(q)}
                          disabled={loading}
                          className="block w-full text-left px-3.5 py-2.5 rounded-xl bg-[var(--color-surface-alt)] border border-transparent text-[0.84rem] text-[var(--color-navy)] leading-snug hover:border-[var(--color-coral)] hover:bg-white hover:shadow-sm transition-all duration-150 active:scale-[0.98]"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  </section>
                ))}
              </div>

              <div className="mt-6 max-w-2xl mx-auto">
                <SchemaExplorer schema={schema} />
              </div>
            </div>
          </div>
        ) : (
          <div className="max-w-4xl mx-auto px-6 py-4">
            <div className="space-y-4">
              {messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  schema={schema}
                />
              ))}
            </div>
            {loading && <WaitingGame />}
            <div ref={bottomRef} />
          </div>
        )}
      </main>

      {loading && (
        <PipelineFlowchart
          activeStage={pipelineProgress.active}
          completedStages={pipelineProgress.completed}
        />
      )}

      <footer className="border-t border-[var(--color-border)] bg-white/80 backdrop-blur-md">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <ChatInput onSend={handleSend} disabled={loading} />
        </div>
      </footer>
    </div>
  );
}
