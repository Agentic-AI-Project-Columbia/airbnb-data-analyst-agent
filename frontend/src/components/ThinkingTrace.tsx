"use client";

import { useState } from "react";
import type { TraceStep } from "./MessageBubble";

function AgentBadge({ name }: { name: string }) {
  const colors: Record<string, string> = {
    Orchestrator: "bg-[var(--color-navy)] text-white",
    "Data Collector": "bg-[var(--color-teal)] text-white",
    "EDA Analyst": "bg-[#6C5CE7] text-white",
    "Hypothesis Generator": "bg-[var(--color-coral)] text-white",
  };
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-md text-[0.7rem] font-semibold tracking-wide whitespace-nowrap ${colors[name] ?? "bg-[var(--color-surface-alt)] text-[var(--color-navy)]"}`}
    >
      {name}
    </span>
  );
}

function CodeBlock({ code, language }: { code: string; language?: string }) {
  const [expanded, setExpanded] = useState(false);
  const lines = code.split("\n");
  const isLong = lines.length > 8;
  const display = expanded ? code : lines.slice(0, 8).join("\n");

  return (
    <div className="relative mt-1.5">
      <div className="text-[0.65rem] uppercase tracking-widest text-[#8a8a9a] mb-1 font-semibold">
        {language ?? "code"}
      </div>
      <pre className="trace-code-block text-[0.78rem] leading-[1.6] rounded-lg p-3 overflow-x-auto">
        <code>{display}</code>
      </pre>
      {isLong && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-[0.75rem] text-[var(--color-teal)] hover:text-[var(--color-teal-dark)] font-medium mt-1 cursor-pointer"
        >
          {expanded ? "Show less" : `Show all ${lines.length} lines`}
        </button>
      )}
    </div>
  );
}

function OutputBlock({ output }: { output: string }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = output.length > 300;
  const display = expanded ? output : output.slice(0, 300);

  return (
    <div className="mt-1.5">
      <div className="text-[0.65rem] uppercase tracking-widest text-[#8a8a9a] mb-1 font-semibold">
        output
      </div>
      <div className="trace-output-block rounded-lg p-3 text-[0.78rem] leading-[1.6] whitespace-pre-wrap break-words font-mono">
        {display}
        {isLong && !expanded && "..."}
      </div>
      {isLong && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-[0.75rem] text-[var(--color-teal)] hover:text-[var(--color-teal-dark)] font-medium mt-1 cursor-pointer"
        >
          {expanded ? "Show less" : "Show full output"}
        </button>
      )}
    </div>
  );
}

function StepIcon({ type }: { type: TraceStep["type"] }) {
  const shared = "w-5 h-5 flex-shrink-0";
  switch (type) {
    case "agent_start":
      return (
        <svg className={shared} viewBox="0 0 20 20" fill="none">
          <circle cx="10" cy="10" r="8" stroke="var(--color-teal)" strokeWidth="1.5" />
          <circle cx="10" cy="10" r="3" fill="var(--color-teal)" />
        </svg>
      );
    case "handoff":
      return (
        <svg className={shared} viewBox="0 0 20 20" fill="none">
          <path d="M4 10h12M12 6l4 4-4 4" stroke="var(--color-coral)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case "tool_call":
      return (
        <svg className={shared} viewBox="0 0 20 20" fill="none">
          <rect x="3" y="4" width="14" height="12" rx="2" stroke="#6C5CE7" strokeWidth="1.5" />
          <path d="M7 9l2 2 4-4" stroke="#6C5CE7" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case "tool_output":
      return (
        <svg className={shared} viewBox="0 0 20 20" fill="none">
          <path d="M6 7l3 3-3 3M10 13h4" stroke="var(--color-teal-dark)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case "message":
      return (
        <svg className={shared} viewBox="0 0 20 20" fill="none">
          <path d="M4 5h12a1 1 0 011 1v7a1 1 0 01-1 1H7l-3 3V6a1 1 0 011-1z" stroke="var(--color-navy)" strokeWidth="1.5" strokeLinejoin="round" />
        </svg>
      );
  }
}

function formatDuration(seconds: number): string {
  if (seconds < 1) return "<1s";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const min = Math.floor(seconds / 60);
  const sec = Math.round(seconds % 60);
  return `${min}m ${sec}s`;
}

function detectLanguage(toolName: string, input: string): string | undefined {
  if (toolName === "query_database") return "sql";
  if (toolName === "run_analysis_code" || toolName === "create_visualization")
    return "python";
  if (input.trimStart().startsWith("SELECT") || input.trimStart().startsWith("WITH"))
    return "sql";
  if (input.includes("import ") || input.includes("def "))
    return "python";
  return undefined;
}

function prettifyToolInput(toolName: string, rawArgs: string): string {
  try {
    const parsed = JSON.parse(rawArgs);
    if (typeof parsed === "object") {
      const key = Object.keys(parsed).find((k) =>
        ["sql", "code", "query"].includes(k)
      );
      if (key && typeof parsed[key] === "string") return parsed[key];
    }
    return rawArgs;
  } catch {
    return rawArgs;
  }
}

export default function ThinkingTrace({ steps }: { steps: TraceStep[] }) {
  const [open, setOpen] = useState(false);

  const meaningfulSteps = steps.filter(
    (s) => s.type !== "agent_start" || s.agent !== "Orchestrator"
  );
  const displaySteps = meaningfulSteps.length > 0 ? meaningfulSteps : steps;
  if (displaySteps.length === 0) return null;

  const totalDuration =
    steps.length >= 2
      ? steps[steps.length - 1].ts - steps[0].ts
      : 0;

  return (
    <div className="mt-4 border-t border-[var(--color-border)] pt-3">
      <button
        onClick={() => setOpen(!open)}
        className="trace-toggle group flex items-center gap-2 text-[0.8rem] font-semibold text-[var(--color-gray-warm)] hover:text-[var(--color-navy)] transition-colors cursor-pointer"
      >
        <svg
          className={`w-3.5 h-3.5 transition-transform duration-200 ${open ? "rotate-90" : ""}`}
          viewBox="0 0 12 12"
          fill="none"
        >
          <path
            d="M4 2l4 4-4 4"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <span>Agent Thinking</span>
        <span className="text-[0.7rem] font-normal text-[var(--color-gray-warm)]">
          {displaySteps.length} steps
          {totalDuration > 0 && ` \u00b7 ${formatDuration(totalDuration)}`}
        </span>
      </button>

      <div
        className={`trace-panel overflow-hidden transition-all duration-300 ease-in-out ${open ? "trace-panel-open mt-3" : "trace-panel-closed"}`}
      >
        <div className="relative pl-7">
          <div className="trace-timeline-line" />

          {displaySteps.map((step, i) => {
            const elapsed =
              i > 0 ? step.ts - displaySteps[i - 1].ts : 0;

            return (
              <div key={i} className="trace-step relative pb-4 last:pb-0">
                <div className="absolute left-[-22px] top-0.5 bg-white rounded-full">
                  <StepIcon type={step.type} />
                </div>

                {step.type === "agent_start" && (
                  <div className="flex items-center gap-2 flex-wrap">
                    <AgentBadge name={step.agent!} />
                    <span className="text-[0.78rem] text-[var(--color-gray-warm)]">
                      started
                    </span>
                    {elapsed > 0 && (
                      <span className="text-[0.68rem] text-[var(--color-gray-warm)] opacity-60">
                        +{formatDuration(elapsed)}
                      </span>
                    )}
                  </div>
                )}

                {step.type === "handoff" && (
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <AgentBadge name={step.source!} />
                    <svg className="w-4 h-4 text-[var(--color-gray-warm)]" viewBox="0 0 16 16" fill="none">
                      <path d="M3 8h10M10 5l3 3-3 3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <AgentBadge name={step.target!} />
                    {elapsed > 0 && (
                      <span className="text-[0.68rem] text-[var(--color-gray-warm)] opacity-60 ml-1">
                        +{formatDuration(elapsed)}
                      </span>
                    )}
                  </div>
                )}

                {step.type === "tool_call" && step.input && (
                  <div>
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      {step.agent && <AgentBadge name={step.agent} />}
                      <span className="text-[0.78rem] text-[var(--color-navy)] font-medium">
                        called{" "}
                        <code className="text-[0.75rem] bg-[var(--color-surface-alt)] px-1.5 py-0.5 rounded">
                          {step.tool}
                        </code>
                      </span>
                      {elapsed > 0 && (
                        <span className="text-[0.68rem] text-[var(--color-gray-warm)] opacity-60">
                          +{formatDuration(elapsed)}
                        </span>
                      )}
                    </div>
                    <CodeBlock
                      code={prettifyToolInput(step.tool!, step.input)}
                      language={detectLanguage(step.tool!, step.input)}
                    />
                  </div>
                )}

                {step.type === "tool_output" && step.output && (
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      {step.agent && <AgentBadge name={step.agent} />}
                      <span className="text-[0.78rem] text-[var(--color-gray-warm)]">
                        returned result
                      </span>
                    </div>
                    <OutputBlock output={step.output} />
                  </div>
                )}

                {step.type === "message" && step.content && (
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      {step.agent && <AgentBadge name={step.agent} />}
                      <span className="text-[0.78rem] text-[var(--color-gray-warm)]">
                        message
                      </span>
                    </div>
                    <p className="text-[0.8rem] text-[var(--color-navy)] leading-relaxed">
                      {step.content}
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
