"use client";

import { useState } from "react";
import type { TraceStep } from "./MessageBubble";
import type { TableSchema } from "./SqlQueryBlock";
import SqlQueryBlock from "./SqlQueryBlock";
import QueryResultSummary from "./QueryResultSummary";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

/* ── Stage definitions ── */

type StageInfo = {
  key: string;
  label: string;
  agent: string;
  color: string;
  borderColor: string;
  bgColor: string;
};

const STAGES: StageInfo[] = [
  {
    key: "collect",
    label: "Collect",
    agent: "Data Collector",
    color: "var(--color-teal)",
    borderColor: "var(--color-teal)",
    bgColor: "rgba(0, 166, 153, 0.04)",
  },
  {
    key: "analyze",
    label: "Analyze",
    agent: "EDA Analyst",
    color: "#6C5CE7",
    borderColor: "#6C5CE7",
    bgColor: "rgba(108, 92, 231, 0.04)",
  },
  {
    key: "synthesize",
    label: "Synthesize",
    agent: "Hypothesis Generator",
    color: "var(--color-coral)",
    borderColor: "var(--color-coral)",
    bgColor: "rgba(255, 90, 95, 0.04)",
  },
  {
    key: "present",
    label: "Present",
    agent: "Presenter",
    color: "#E17055",
    borderColor: "#E17055",
    bgColor: "rgba(225, 112, 85, 0.04)",
  },
];

function getStageForAgent(agentName: string): StageInfo | undefined {
  return STAGES.find((s) => s.agent === agentName);
}

/* ── Helpers ── */

function formatDuration(seconds: number): string {
  if (seconds < 1) return "<1s";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const min = Math.floor(seconds / 60);
  const sec = Math.round(seconds % 60);
  return `${min}m ${sec}s`;
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

function detectLanguage(toolName: string, input: string): string | undefined {
  if (toolName === "query_database") return "sql";
  if (toolName === "run_analysis_code" || toolName === "create_visualization")
    return "python";
  if (input.trimStart().startsWith("SELECT") || input.trimStart().startsWith("WITH"))
    return "sql";
  if (input.includes("import ") || input.includes("def ")) return "python";
  return undefined;
}

/* ── Stage grouping ── */

type StageGroup = {
  stage: StageInfo;
  steps: TraceStep[];
  startTs: number;
  endTs: number;
};

function groupStepsByStage(steps: TraceStep[]): StageGroup[] {
  const groups: StageGroup[] = [];
  let currentStage: StageInfo | undefined;
  let currentSteps: TraceStep[] = [];
  let startTs = 0;

  for (const step of steps) {
    const agent = step.agent || step.target || step.source;
    if (!agent) continue;

    const stage = getStageForAgent(agent);
    if (!stage) {
      // Orchestrator steps — skip
      continue;
    }

    if (stage.key !== currentStage?.key) {
      if (currentStage && currentSteps.length > 0) {
        groups.push({
          stage: currentStage,
          steps: currentSteps,
          startTs,
          endTs: currentSteps[currentSteps.length - 1].ts,
        });
      }
      currentStage = stage;
      currentSteps = [step];
      startTs = step.ts;
    } else {
      currentSteps.push(step);
    }
  }

  if (currentStage && currentSteps.length > 0) {
    groups.push({
      stage: currentStage,
      steps: currentSteps,
      startTs,
      endTs: currentSteps[currentSteps.length - 1].ts,
    });
  }

  return groups;
}

/* ── Sub-components ── */

function PipelineProgressBar({ groups, totalDuration }: { groups: StageGroup[]; totalDuration: number }) {
  const completedKeys = new Set(groups.map((g) => g.stage.key));

  return (
    <div className="flex items-center gap-0 mb-5">
      {STAGES.map((stage, i) => {
        const group = groups.find((g) => g.stage.key === stage.key);
        const isComplete = completedKeys.has(stage.key);
        const duration = group ? group.endTs - group.startTs : 0;

        return (
          <div key={stage.key} className="flex items-center">
            <div
              className="pipeline-stage"
              style={{
                borderColor: isComplete ? stage.color : "var(--color-border)",
                background: isComplete ? stage.bgColor : "transparent",
              }}
            >
              {isComplete ? (
                <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 16 16" fill="none">
                  <path
                    d="M3 8.5l3.5 3.5L13 4"
                    stroke={stage.color}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              ) : (
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ background: "var(--color-border)" }}
                />
              )}
              <span
                className="text-[0.75rem] font-semibold"
                style={{ color: isComplete ? stage.color : "var(--color-gray-warm)" }}
              >
                {stage.label}
              </span>
              {isComplete && duration > 0 && (
                <span className="text-[0.65rem] opacity-60" style={{ color: stage.color }}>
                  {formatDuration(duration)}
                </span>
              )}
            </div>
            {i < STAGES.length - 1 && (
              <div
                className="w-8 h-[2px] mx-0.5"
                style={{
                  background: isComplete ? stage.color : "var(--color-border)",
                  opacity: isComplete ? 0.4 : 1,
                }}
              />
            )}
          </div>
        );
      })}
      {totalDuration > 0 && (
        <span className="ml-auto text-[0.7rem] text-[var(--color-gray-warm)]">
          Total: {formatDuration(totalDuration)}
        </span>
      )}
    </div>
  );
}

function CodeBlock({ code, language }: { code: string; language?: string }) {
  const [expanded, setExpanded] = useState(false);
  const lines = code.split("\n");
  const isLong = lines.length > 8;
  const display = expanded ? code : lines.slice(0, 8).join("\n");

  return (
    <div className="mt-1.5">
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

function ExecutionStatus({ step }: { step: TraceStep }) {
  const exitCode = (step as Record<string, unknown>).exit_code as number | undefined;
  if (exitCode !== undefined) {
    const success = exitCode === 0;
    return (
      <div className={`flex items-center gap-1.5 mt-2 text-[0.75rem] font-medium ${success ? "text-[var(--color-teal)]" : "text-[var(--color-coral)]"}`}>
        {success ? (
          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
            <path d="M3 8.5l3.5 3.5L13 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        ) : (
          <svg className="w-4 h-4" viewBox="0 0 16 16" fill="none">
            <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        )}
        {success ? "Executed successfully" : `Failed (exit code ${exitCode})`}
      </div>
    );
  }
  return null;
}

function StageCard({
  group,
  schema,
}: {
  group: StageGroup;
  schema: Record<string, TableSchema> | null;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const { stage, steps } = group;
  const duration = group.endTs - group.startTs;

  const toolCalls = steps.filter((s) => s.type === "tool_call");
  const toolOutputs = steps.filter((s) => s.type === "tool_output");
  const messages = steps.filter((s) => s.type === "message");
  const artifacts: string[] = steps.flatMap((s) => {
    const a = (s as Record<string, unknown>).artifacts;
    if (!Array.isArray(a)) return [];
    return a.filter((item): item is string => typeof item === "string");
  });

  return (
    <div
      className="stage-card"
      style={{
        borderLeftColor: stage.borderColor,
        background: stage.bgColor,
      }}
    >
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center gap-2 w-full text-left cursor-pointer"
      >
        <svg
          className={`w-3 h-3 transition-transform duration-200 ${collapsed ? "" : "rotate-90"}`}
          viewBox="0 0 12 12"
          fill="none"
        >
          <path
            d="M4 2l4 4-4 4"
            stroke={stage.color}
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <span
          className="text-[0.82rem] font-bold"
          style={{ color: stage.color }}
        >
          {stage.label}
        </span>
        <span
          className="inline-flex items-center px-2 py-0.5 rounded-md text-[0.68rem] font-semibold tracking-wide text-white"
          style={{ background: stage.color }}
        >
          {stage.agent}
        </span>
        {duration > 0 && (
          <span className="text-[0.68rem] text-[var(--color-gray-warm)] ml-auto">
            {formatDuration(duration)}
          </span>
        )}
      </button>

      {!collapsed && (
        <div className="mt-3 space-y-3">
          {/* SQL queries (Data Collector) */}
          {toolCalls.map((tc, i) => {
            const toolName = tc.tool || "";
            const rawInput = typeof tc.input === "string" ? tc.input : "";
            const lang = detectLanguage(toolName, rawInput);
            const code = prettifyToolInput(toolName, rawInput);
            const matchingOutput = toolOutputs[i];
            const raw = matchingOutput as Record<string, unknown> | undefined;
            const rowCount = typeof raw?.row_count === "number" ? raw.row_count : undefined;
            const columns = Array.isArray(raw?.columns) ? (raw.columns as string[]) : undefined;
            const preview = Array.isArray(raw?.preview) ? (raw.preview as Record<string, unknown>[]) : undefined;
            const tables = Array.isArray((tc as Record<string, unknown>).tables) ? ((tc as Record<string, unknown>).tables as string[]) : undefined;

            return (
              <div key={i}>
                {lang === "sql" ? (
                  <SqlQueryBlock sql={code} tables={tables} schema={schema} />
                ) : (
                  <CodeBlock code={code} language={lang} />
                )}

                {matchingOutput && (
                  <>
                    <QueryResultSummary
                      rowCount={rowCount}
                      columns={columns}
                      preview={preview}
                    />
                    <ExecutionStatus step={matchingOutput} />
                  </>
                )}
              </div>
            );
          })}

          {/* Agent messages — findings / reasoning */}
          {messages.map((msg, i) => (
            <div key={`msg-${i}`} className="text-[0.8rem] text-[var(--color-navy)] leading-relaxed pl-1">
              {msg.content}
            </div>
          ))}

          {/* Inline artifact thumbnails */}
          {artifacts.length > 0 && (
            <div className="flex gap-2 flex-wrap mt-2">
              {artifacts.map((art, i) => {
                const url = `${BACKEND_URL}${art}`;
                const name = art.split("/").pop() || art;
                if (/\.(png|jpe?g|gif|webp|svg)$/i.test(art)) {
                  return (
                    <a
                      key={i}
                      href={url}
                      target="_blank"
                      rel="noreferrer"
                      className="block w-32 h-24 rounded-lg overflow-hidden border border-[var(--color-border)] hover:border-[var(--color-coral)] transition-colors"
                    >
                      <img
                        src={url}
                        alt={name}
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                    </a>
                  );
                }
                return null;
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Main component ── */

export default function ThinkingTrace({
  steps,
  schema,
}: {
  steps: TraceStep[];
  schema: Record<string, TableSchema> | null;
}) {
  const [open, setOpen] = useState(true);

  if (steps.length === 0) return null;

  const groups = groupStepsByStage(steps);
  const totalDuration =
    steps.length >= 2 ? steps[steps.length - 1].ts - steps[0].ts : 0;

  return (
    <div className="mt-5 border-t border-[var(--color-border)] pt-4">
      <button
        onClick={() => setOpen(!open)}
        className="trace-toggle group flex items-center gap-2 text-[0.82rem] font-semibold text-[var(--color-navy)] hover:text-[var(--color-teal)] transition-colors cursor-pointer mb-3"
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
        <span>Agent Trace</span>
        <span className="text-[0.7rem] font-normal text-[var(--color-gray-warm)]">
          {groups.length} stages
          {totalDuration > 0 && ` \u00b7 ${formatDuration(totalDuration)}`}
        </span>
      </button>

      {open && (
        <div className="space-y-3">
          <PipelineProgressBar groups={groups} totalDuration={totalDuration} />
          {groups.map((group, i) => (
            <StageCard key={i} group={group} schema={schema} />
          ))}
        </div>
      )}
    </div>
  );
}
