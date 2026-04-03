"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import Header from "@/components/Header";
import ChatInput from "@/components/ChatInput";
import MessageBubble, {
  type Message,
  type TraceStep,
} from "@/components/MessageBubble";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

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

  const handleSend = useCallback(
    async (question: string) => {
      const startedAt = Date.now() / 1000;
      const history = messages
        .filter(
          (message) =>
            message.role === "user" || message.role === "assistant"
        )
        .map((message) => ({
          role: message.role,
          content: message.content,
        }));

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

      try {
        const res = await fetch(`${BACKEND_URL}/api/analyze`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question, history }),
        });

        setMessages((prev) => prev.filter((m) => m.role !== "status"));

        if (!res.ok) {
          const err = await res.json();
          addMessage({
            id: (Date.now() + 2).toString(),
            role: "assistant",
            content: `**Error:** ${err.error || "Something went wrong"}`,
          });
          return;
        }

        const data = await res.json();
        const trace =
          Array.isArray(data.trace) && data.trace.length > 0
            ? data.trace
            : buildFallbackTrace(question, data.answer, startedAt);

        addMessage({
          id: (Date.now() + 2).toString(),
          role: "assistant",
          content: data.answer,
          artifacts: data.artifacts,
          trace,
        });
      } catch {
        setMessages((prev) => prev.filter((m) => m.role !== "status"));
        addMessage({
          id: (Date.now() + 2).toString(),
          role: "assistant",
          content: `**Connection error:** Could not reach the backend. Make sure the server is running at ${BACKEND_URL}`,
        });
      } finally {
        setLoading(false);
      }
    },
    [addMessage, buildFallbackTrace, messages]
  );

  return (
    <div className="flex flex-col h-screen">
      <Header />

      <main className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="max-w-4xl mx-auto px-6 py-8">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
              <div className="w-16 h-16 gradient-coral rounded-2xl flex items-center justify-center mb-6 shadow-lg">
                <svg
                  width="32"
                  height="32"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="white"
                  strokeWidth="1.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M3 3v18h18" />
                  <path d="M7 16l4-8 4 4 4-10" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-[var(--color-navy)] mb-2">
                What would you like to explore?
              </h2>
              <p className="text-[var(--color-gray-warm)] max-w-md mb-2 text-[0.95rem]">
                Ask any question about NYC Airbnb data. Our multi-agent system
                will collect data, perform analysis, and form a hypothesis with
                supporting visualizations.
              </p>
              <div className="flex flex-wrap justify-center gap-2 mt-2 text-xs text-[var(--color-gray-warm)]">
                <span className="px-2 py-1 rounded-md bg-[var(--color-surface-alt)] border border-[var(--color-border)]">
                  36K+ listings
                </span>
                <span className="px-2 py-1 rounded-md bg-[var(--color-surface-alt)] border border-[var(--color-border)]">
                  13M+ calendar rows
                </span>
                <span className="px-2 py-1 rounded-md bg-[var(--color-surface-alt)] border border-[var(--color-border)]">
                  1M+ reviews
                </span>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </main>

      <footer className="border-t border-[var(--color-border)] bg-white/80 backdrop-blur-md">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <ChatInput onSend={handleSend} disabled={loading} />
        </div>
      </footer>
    </div>
  );
}
