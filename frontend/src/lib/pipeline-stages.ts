export type StageInfo = {
  key: string;
  label: string;
  agent: string;
  color: string;
  borderColor: string;
  bgColor: string;
};

export const STAGES: StageInfo[] = [
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

export function getStageForAgent(agentName: string): StageInfo | undefined {
  return STAGES.find((s) => s.agent === agentName);
}
