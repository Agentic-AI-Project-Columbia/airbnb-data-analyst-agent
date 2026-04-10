"use client";

import { useState, useEffect, use } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import ThinkingTrace from "@/components/ThinkingTrace";
import type { TraceStep } from "@/components/MessageBubble";

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

type ShareData = {
  id: string;
  question: string;
  answer: string;
  artifacts: string[];
  trace: TraceStep[];
  created_at: number;
};

function ImageArtifact({ url, name }: { url: string; name: string }) {
  const [failed, setFailed] = useState(false);

  return (
    <div className="rounded-lg overflow-hidden border border-[var(--color-border)] bg-[var(--color-surface-alt)]">
      {!failed ? (
        <img
          src={url}
          alt={name}
          className="w-full"
          loading="lazy"
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="px-4 py-6 text-sm text-[var(--color-gray-warm)]">
          Preview unavailable for this chart.
        </div>
      )}
      <div className="flex items-center justify-between border-t border-[var(--color-border)] px-4 py-2 text-sm">
        <span className="font-medium text-[var(--color-navy)]">{name}</span>
        <a
          href={url}
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

export default function SharePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [data, setData] = useState<ShareData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${BACKEND_URL}/api/share/${id}`)
      .then((res) => {
        if (!res.ok) throw new Error("Share not found");
        return res.json();
      })
      .then((d) => setData(d))
      .catch((e) => setError(e.message));
  }, [id]);

  if (error) {
    return (
      <div className="flex flex-col h-screen">
        <header className="border-b border-[var(--color-border)] bg-white/80 backdrop-blur-md sticky top-0 z-50">
          <div className="max-w-4xl mx-auto px-6 py-4 flex items-center gap-3">
            <div className="w-9 h-9 gradient-coral rounded-lg flex items-center justify-center shadow-sm">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 3v18h18" />
                <path d="M7 16l4-8 4 4 4-10" />
              </svg>
            </div>
            <h1 className="text-lg font-bold tracking-tight text-[var(--color-navy)]">
              Airbnb Data Analyst
            </h1>
          </div>
        </header>
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <p className="text-lg font-semibold text-[var(--color-navy)] mb-2">
              Share not found
            </p>
            <p className="text-sm text-[var(--color-gray-warm)]">
              This link may have expired or been removed.
            </p>
            <a
              href="/"
              className="inline-block mt-4 text-sm font-medium gradient-coral text-white px-4 py-2 rounded-full hover:opacity-90 transition-all"
            >
              Go to Airbnb Data Analyst
            </a>
          </div>
        </main>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex flex-col h-screen">
        <header className="border-b border-[var(--color-border)] bg-white/80 backdrop-blur-md sticky top-0 z-50">
          <div className="max-w-4xl mx-auto px-6 py-4 flex items-center gap-3">
            <div className="w-9 h-9 gradient-coral rounded-lg flex items-center justify-center shadow-sm">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 3v18h18" />
                <path d="M7 16l4-8 4 4 4-10" />
              </svg>
            </div>
            <h1 className="text-lg font-bold tracking-tight text-[var(--color-navy)]">
              Airbnb Data Analyst
            </h1>
          </div>
        </header>
        <main className="flex-1 flex items-center justify-center">
          <div className="thinking-dots flex gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--color-teal)]" />
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--color-teal)]" />
            <span className="w-2.5 h-2.5 rounded-full bg-[var(--color-teal)]" />
          </div>
        </main>
      </div>
    );
  }

  const imageArtifacts = (data.artifacts || []).filter((a) =>
    /\.(png|jpe?g|gif|webp|svg)$/i.test(a)
  );
  const otherArtifacts = (data.artifacts || []).filter(
    (a) => !/\.(png|jpe?g|gif|webp|svg)$/i.test(a)
  );

  return (
    <div className="flex flex-col h-screen">
      <header className="border-b border-[var(--color-border)] bg-white/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center gap-3">
          <a href="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
            <div className="w-9 h-9 gradient-coral rounded-lg flex items-center justify-center shadow-sm">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 3v18h18" />
                <path d="M7 16l4-8 4 4 4-10" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-[var(--color-navy)]">
                Airbnb Data Analyst
              </h1>
              <p className="text-xs text-[var(--color-gray-warm)]">
                Shared analysis
              </p>
            </div>
          </a>
          <div className="ml-auto">
            <a
              href="/"
              className="text-xs font-medium gradient-coral text-white px-3 py-1.5 rounded-full hover:opacity-90 active:scale-95 transition-all duration-150"
            >
              Try it yourself
            </a>
          </div>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="max-w-4xl mx-auto px-6 py-6 space-y-4">
          {/* User question */}
          <div className="flex justify-end animate-fade-in-up">
            <div className="max-w-[85%] rounded-2xl px-5 py-3.5 gradient-coral text-white rounded-br-md">
              <p className="text-[0.95rem] leading-relaxed">{data.question}</p>
            </div>
          </div>

          {/* Assistant answer */}
          <div className="flex justify-start animate-fade-in-up">
            <div className="max-w-[85%] rounded-2xl px-5 py-3.5 bg-white border border-[var(--color-border)] rounded-bl-md shadow-sm">
              <div className="prose-chat text-[0.95rem]">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {data.answer}
                </ReactMarkdown>
              </div>

              {imageArtifacts.length > 0 && (
                <div className="mt-4 space-y-3">
                  {imageArtifacts.map((artifact, i) => (
                    <ImageArtifact
                      key={i}
                      url={`${BACKEND_URL}${artifact}`}
                      name={artifact.split("/").pop() || artifact}
                    />
                  ))}
                </div>
              )}

              {otherArtifacts.length > 0 && (
                <div className="mt-4 space-y-2">
                  {otherArtifacts.map((artifact, i) => (
                    <a
                      key={i}
                      href={`${BACKEND_URL}${artifact}`}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center justify-between rounded-lg border border-[var(--color-border)] bg-[var(--color-surface-alt)] px-4 py-3 text-sm hover:border-[var(--color-coral)]"
                    >
                      <span className="font-medium text-[var(--color-navy)]">
                        {artifact.split("/").pop() || artifact}
                      </span>
                      <span className="text-[var(--color-gray-warm)]">
                        Open file
                      </span>
                    </a>
                  ))}
                </div>
              )}

              {data.trace && data.trace.length > 0 && (
                <ThinkingTrace steps={data.trace} schema={null} />
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
