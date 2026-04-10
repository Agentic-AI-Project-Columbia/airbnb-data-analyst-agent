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
    color: "#FC642D",
    borderColor: "#FC642D",
    bgColor: "rgba(252, 100, 45, 0.04)",
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
    color: "#484848",
    borderColor: "#484848",
    bgColor: "rgba(72, 72, 72, 0.04)",
  },
];

export function getStageForAgent(agentName: string): StageInfo | undefined {
  return STAGES.find((s) => s.agent === agentName);
}
