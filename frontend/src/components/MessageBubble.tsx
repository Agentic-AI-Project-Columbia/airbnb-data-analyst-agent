"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ThinkingTrace from "./ThinkingTrace";

export type TraceStep = {
  type: "agent_start" | "handoff" | "tool_call" | "tool_output" | "message";
  agent?: string;
  source?: string;
  target?: string;
  tool?: string;
  input?: string;
  output?: string;
  content?: string;
  ts: number;
};

export type Message = {
  id: string;
  role: "user" | "assistant" | "status";
  content: string;
  artifacts?: string[];
  agent?: string;
  trace?: TraceStep[];
};

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

function getArtifactName(path: string): string {
  return path.split("/").pop() || path;
}

function isImageArtifact(path: string): boolean {
  return /\.(png|jpe?g|gif|webp|svg)$/i.test(path);
}

export default function MessageBubble({ message }: { message: Message }) {
  if (message.role === "status") {
    return (
      <div className="flex items-center gap-2 px-4 py-2 animate-fade-in-up">
        <div className="thinking-dots flex gap-1">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-teal)]" />
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-teal)]" />
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-teal)]" />
        </div>
        <span className="text-sm text-[var(--color-gray-warm)] italic">
          {message.agent && (
            <span className="font-semibold text-[var(--color-teal)] mr-1">
              {message.agent}:
            </span>
          )}
          {message.content}
        </span>
      </div>
    );
  }

  const isUser = message.role === "user";

  return (
    <div
      className={`flex animate-fade-in-up ${isUser ? "justify-end" : "justify-start"}`}
    >
      <div
        className={`max-w-[85%] rounded-2xl px-5 py-3.5 ${
          isUser
            ? "gradient-coral text-white rounded-br-md"
            : "bg-white border border-[var(--color-border)] rounded-bl-md shadow-sm"
        }`}
      >
        {isUser ? (
          <p className="text-[0.95rem] leading-relaxed">{message.content}</p>
        ) : (
          <div className="prose-chat text-[0.95rem]">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {message.artifacts && message.artifacts.length > 0 && (
          <div className="mt-4 space-y-3">
            {message.artifacts.map((artifact, i) => {
              const artifactUrl = `${BACKEND_URL}${artifact}`;
              const artifactName = getArtifactName(artifact);

              if (isImageArtifact(artifact)) {
                return (
                  <div
                    key={i}
                    className="rounded-lg overflow-hidden border border-[var(--color-border)]"
                  >
                    <img
                      src={artifactUrl}
                      alt={artifactName}
                      className="w-full"
                      loading="lazy"
                    />
                  </div>
                );
              }

              return (
                <a
                  key={i}
                  href={artifactUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center justify-between rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-alt)] px-4 py-3 text-sm hover:border-[var(--color-coral)]"
                >
                  <span className="font-medium text-[var(--color-navy)]">
                    {artifactName}
                  </span>
                  <span className="text-[var(--color-gray-warm)]">Open file</span>
                </a>
              );
            })}
          </div>
        )}

        {message.trace && message.trace.length > 0 && (
          <ThinkingTrace steps={message.trace} />
        )}
      </div>
    </div>
  );
}
