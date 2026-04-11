"use client";

import Image from "next/image";
import { useState, memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ThinkingTrace from "./ThinkingTrace";
import type { TableSchema } from "./SqlQueryBlock";

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
  tables?: string[];
  row_count?: number;
  returned_row_count?: number;
  truncated?: boolean;
  columns?: string[];
  preview?: Record<string, unknown>[];
  exit_code?: number;
  artifacts?: string[];
};

export type Message = {
  id: string;
  role: "user" | "assistant" | "status";
  content: string;
  artifacts?: string[];
  agent?: string;
  trace?: TraceStep[];
  question?: string;
};

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

function getArtifactName(path: string): string {
  return path.split("/").pop() || path;
}

function isImageArtifact(path: string): boolean {
  return /\.(png|jpe?g|gif|webp|svg)$/i.test(path);
}

function ImageArtifact({
  artifactUrl,
  artifactName,
}: {
  artifactUrl: string;
  artifactName: string;
}) {
  const [failed, setFailed] = useState(false);

  return (
    <div className="rounded-lg overflow-hidden border border-[var(--color-border)] bg-[var(--color-surface-alt)]">
      {!failed ? (
        <Image
          src={artifactUrl}
          alt={artifactName}
          width={1200}
          height={800}
          unoptimized
          className="w-full"
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="px-4 py-6 text-sm text-[var(--color-gray-warm)]">
          Preview unavailable for this chart.
        </div>
      )}
      <div className="flex items-center justify-between border-t border-[var(--color-border)] px-4 py-2 text-sm">
        <span className="font-medium text-[var(--color-navy)]">
          {artifactName}
        </span>
        <a
          href={artifactUrl}
          target="_blank"
          rel="noreferrer"
          className="text-[var(--color-coral)] hover:underline"
        >
          Open image
        </a>
      </div>
    </div>
  );
}

function InlineChartImage({ src, alt }: { src: string; alt: string }) {
  const [failed, setFailed] = useState(false);
  if (failed) return null;
  return (
    <Image
      src={src}
      alt={alt}
      width={1200}
      height={800}
      unoptimized
      className="inline-chart"
      onError={() => setFailed(true)}
    />
  );
}

function ShareButton({
  message,
}: {
  message: Message;
}) {
  const [state, setState] = useState<"idle" | "loading" | "done">("idle");
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleShare = async () => {
    if (state === "done" && shareUrl) {
      // Already have a link — just show it again
      return;
    }

    setState("loading");
    try {
      const res = await fetch(`${BACKEND_URL}/api/share`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: message.question || "",
          answer: message.content,
          artifacts: message.artifacts || [],
          trace: message.trace || [],
        }),
      });
      const data = await res.json();
      if (data.id) {
        const url = `${window.location.origin}/share/${data.id}`;
        setShareUrl(url);
        setState("done");
      } else {
        setState("idle");
      }
    } catch {
      setState("idle");
    }
  };

  const handleCopy = async () => {
    if (!shareUrl) return;
    try {
      await navigator.clipboard.writeText(shareUrl);
    } catch {
      const ta = document.createElement("textarea");
      ta.value = shareUrl;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="mt-3">
      {!shareUrl ? (
        <button
          onClick={handleShare}
          disabled={state === "loading"}
          className="share-btn flex items-center gap-1.5 text-xs text-[var(--color-gray-warm)] hover:text-[var(--color-coral)] transition-colors duration-150 disabled:opacity-50"
        >
          {state === "loading" ? (
            <>
              <svg className="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 12a9 9 0 1 1-6.219-8.56" />
              </svg>
              Creating link...
            </>
          ) : (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8" />
                <polyline points="16 6 12 2 8 6" />
                <line x1="12" y1="2" x2="12" y2="15" />
              </svg>
              Share
            </>
          )}
        </button>
      ) : (
        <div className="flex items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-alt)] px-3 py-2">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--color-teal)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
          </svg>
          <input
            readOnly
            value={shareUrl}
            className="flex-1 bg-transparent text-xs text-[var(--color-navy)] outline-none truncate min-w-0"
            onFocus={(e) => e.target.select()}
          />
          <button
            onClick={handleCopy}
            className="shrink-0 text-xs font-medium px-2.5 py-1 rounded-md gradient-coral text-white hover:opacity-90 active:scale-95 transition-all duration-150"
          >
            {copied ? "Copied!" : "Copy"}
          </button>
        </div>
      )}
    </div>
  );
}

function MessageBubbleInner({
  message,
  schema,
}: {
  message: Message;
  schema: Record<string, TableSchema> | null;
}) {
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
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                img: ({ src, alt }) => {
                  const srcStr = typeof src === "string" ? src : "";
                  const resolvedSrc = srcStr.startsWith("/artifacts/")
                    ? `${BACKEND_URL}${srcStr}`
                    : srcStr;
                  return (
                    <InlineChartImage
                      src={resolvedSrc || ""}
                      alt={alt || ""}
                    />
                  );
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {message.artifacts && message.artifacts.length > 0 && (() => {
          // Find artifact paths already embedded inline in the markdown
          const inlineRefs = new Set(
            (message.content.match(/!\[.*?\]\((\/artifacts\/[^)]+)\)/g) || [])
              .map((m) => m.match(/\((\/artifacts\/[^)]+)\)/)?.[1])
              .filter((p): p is string => !!p),
          );
          const remaining = message.artifacts
            .filter((a): a is string => typeof a === "string" && a.length > 0)
            .filter((a) => !inlineRefs.has(a));

          if (remaining.length === 0) return null;

          return (
            <div className="mt-4 space-y-3">
              {remaining.map((artifact, i) => {
                const artifactUrl = `${BACKEND_URL}${artifact}`;
                const artifactName = getArtifactName(artifact);

                if (isImageArtifact(artifact)) {
                  return (
                    <ImageArtifact
                      key={i}
                      artifactUrl={artifactUrl}
                      artifactName={artifactName}
                    />
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
          );
        })()}

        {!isUser && (
          <ShareButton message={message} />
        )}

        {message.trace && message.trace.length > 0 && (
          <ThinkingTrace steps={message.trace} schema={schema} />
        )}
      </div>
    </div>
  );
}

const MessageBubble = memo(MessageBubbleInner);
export default MessageBubble;
