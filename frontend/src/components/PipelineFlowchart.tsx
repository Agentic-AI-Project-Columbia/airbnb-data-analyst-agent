"use client";

import { memo } from "react";
import { STAGES } from "@/lib/pipeline-stages";

type PipelineFlowchartProps = {
  activeStage: string | null;
  completedStages: Set<string>;
};

function CheckIcon({ color }: { color: string }) {
  return (
    <svg className="w-3.5 h-3.5 shrink-0" viewBox="0 0 16 16" fill="none">
      <path
        d="M3 8.5l3.5 3.5L13 4"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function PulsingDot({ color }: { color: string }) {
  return (
    <span className="relative flex w-3 h-3 shrink-0">
      <span
        className="absolute inset-0 rounded-full opacity-40 animate-ping"
        style={{ backgroundColor: color }}
      />
      <span
        className="relative inline-flex w-3 h-3 rounded-full"
        style={{ backgroundColor: color }}
      />
    </span>
  );
}

function GrayDot() {
  return (
    <span
      className="w-2.5 h-2.5 rounded-full shrink-0"
      style={{ backgroundColor: "var(--color-border)" }}
    />
  );
}

function LoopIcon({ color }: { color: string }) {
  return (
    <svg className="w-3 h-3 shrink-0 opacity-60" viewBox="0 0 16 16" fill="none">
      <path
        d="M12 5.5A4.5 4.5 0 0 0 4.5 4M4 10.5A4.5 4.5 0 0 0 11.5 12"
        stroke={color}
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path d="M5.5 1.5L4.5 4l2.5 1" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M10.5 14.5l1-2.5-2.5-1" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function PipelineFlowchartInner({
  activeStage,
  completedStages,
}: PipelineFlowchartProps) {
  return (
    <div
      className="fixed right-6 z-40 hidden sm:flex flex-col items-center
                 bg-white/90 backdrop-blur-sm border border-[var(--color-border)]
                 rounded-2xl shadow-lg animate-fade-in-up"
      style={{ padding: "16px 20px", width: "156px", top: "50%", transform: "translateY(-50%)" }}
    >
      <p className="text-[0.6rem] uppercase tracking-[0.12em] text-[var(--color-gray-warm)] font-semibold mb-3">
        Pipeline
      </p>

      {STAGES.map((stage, i) => {
        const isCompleted = completedStages.has(stage.key);
        const isActive = activeStage === stage.key;
        const state = isCompleted ? "completed" : isActive ? "active" : "pending";

        const nodeColor =
          state === "pending" ? "var(--color-gray-warm)" : stage.color;
        const nodeBorder =
          state === "pending" ? "var(--color-border)" : stage.color;
        const nodeBg =
          state === "completed"
            ? stage.bgColor
            : state === "active"
              ? stage.bgColor
              : "transparent";

        return (
          <div key={stage.key} className="flex flex-col items-center w-full">
            {/* Connector line above (skip for first node) */}
            {i > 0 && (
              <div
                className="w-[2px] h-4 transition-colors duration-500"
                style={{
                  backgroundColor: completedStages.has(STAGES[i - 1].key)
                    ? STAGES[i - 1].color
                    : "var(--color-border)",
                }}
              />
            )}

            {/* Node */}
            <div
              className={`flex items-center gap-2 w-full px-3 py-1.5 rounded-full border-[1.5px] transition-all duration-500 ${
                state === "active" ? "pipeline-node-active" : ""
              }`}
              style={{
                borderColor: nodeBorder,
                background: nodeBg,
              }}
            >
              {state === "completed" ? (
                <CheckIcon color={stage.color} />
              ) : state === "active" ? (
                <PulsingDot color={stage.color} />
              ) : (
                <GrayDot />
              )}
              <span
                className="text-[0.72rem] font-semibold truncate"
                style={{ color: nodeColor }}
              >
                {stage.label}
              </span>
              {stage.key === "analyze" && state !== "pending" && (
                <LoopIcon color={stage.color} />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

const PipelineFlowchart = memo(PipelineFlowchartInner, (prev, next) => {
  if (prev.activeStage !== next.activeStage) return false;
  if (prev.completedStages.size !== next.completedStages.size) return false;
  for (const key of prev.completedStages) {
    if (!next.completedStages.has(key)) return false;
  }
  return true;
});

export default PipelineFlowchart;
