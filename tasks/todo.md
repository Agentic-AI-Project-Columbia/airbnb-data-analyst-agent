- [x] Confirm the runnable evaluation entry points and active model-provider configuration.
- [x] Run a targeted end-to-end pipeline evaluation on a small question set.
- [x] Inspect stage-by-stage behavior, tool calls, artifacts, timings, and final outputs.
- [x] Summarize what the current pipeline proves, plus any gaps or failures that still matter.

## Review

- Verified evaluation entry point: `python evaluate.py --models google/gemini-2.5-flash --questions 1 2 3 --output evaluation_rerun_20260411.json`.
- Confirmed live provider config is present in `backend/.env` without exposing secret values.
- Rerun result on Gemini 2.5 Flash: 3/3 questions returned `success`, but quality was inconsistent. Q1 took 148.6s with 2 charts; Q2 took 32.5s with 0 charts and empty final answer text; Q3 took 28.8s with 0 charts and a 212-character answer. Average score was 51.7/100.
- Direct app-pipeline trace on the default model (`openai/gpt-5.4-mini` via OpenRouter) for the host-quality question behaved much better: final answer length 2789, 3 chart artifacts, 8 tool calls, and visible four-stage orchestration plus presenter retries after an initial bad artifact path.
- Main takeaway: the architecture is real and the live app pipeline can produce strong runs, but behavior is model-sensitive and the standalone evaluation harness is materially weaker than the README currently implies.

## 2026-04-11 Quality Follow-Up

- [x] Review current README claims and confirm which previously reported issues remain unresolved.
- [x] Fix frontend validation failures and runtime issues in the trace/share flows.
- [x] Fix backend SQL result metadata so row counts are accurate and structured.
- [x] Enable follow-up conversation history in the frontend/backend flow.
- [x] Align backend execution and dependency implementation with the documented behavior without changing the current README illustrations.
- [x] Run verification checks and document results.

### Review

- README illustrations are still present. The earlier README/code mismatch is reduced, but not fully eliminated: the README still describes the Python execution environment as "sandboxed" and still overstates typed inter-agent structured output.
- Frontend fixes completed: lint passes, the trace hook-order bug is gone, share-page navigation uses `Link`, artifact images use `next/image`, the landing page now shows the data overview and schema explorer, and chat follow-ups now send prior history.
- Backend fixes completed: SQL responses now report honest total row counts plus truncation metadata, tool outputs are serialized through Pydantic models, code execution runs in a subprocess, import restrictions are enforced, and `openai` is now declared explicitly in the Python dependencies.
- Verification completed:
- `npm run lint`
- `npm run build`
- `python -m py_compile` across backend Python files
- Backend smoke tests covering SQL truncation metadata, successful chart generation, and blocked disallowed imports

## 2026-04-11 README Accuracy Audit

- [x] Re-read the current `README.md` after the recent README edits.
- [x] Compare each major README claim against the current frontend, backend, deployment, and evaluation code.
- [x] Summarize which claims are now accurate versus which remain overstated or stale.
- [x] Document the audit result in the review section.

### Review

- Verdict: the README is improved, but it is not yet fully accurate.
- Confirmed accurate after the recent code fixes: the landing page now shows a live dataset overview and schema explorer; the frontend sends follow-up history; SQL responses now expose honest total row counts plus truncation metadata; Python execution now runs in a subprocess with import validation; lint, build, py_compile, and backend smoke tests all pass.
- Still inaccurate or overstated:
- The README still describes Python execution as "sandboxed" and in one section still says it runs in a daemon thread, while the implementation uses a subprocess plus an import allowlist and is not a true sandbox.
- The README still claims agents are stateless across questions with no conversational memory, but the frontend now sends prior chat history and the backend uses that history to resolve follow-up questions.
- The README still claims a 20-question, 100% successful evaluation suite, but the checked-in evaluation harness defines 7 questions and the local evaluation artifacts inspected were only single-question runs.
- The README still says the backend Docker image is multi-stage, but the Dockerfile is single-stage.
- The README still overstates "typed inter-agent data flow": Pydantic now structures tool payloads, but the stage-to-stage agent flow is still plain text context threading rather than typed contracts.
- The README dependency block is stale because `openai>=1.0.0` is now a direct backend dependency but is not listed there.

## 2026-04-11 Agent Code Failure Troubleshooting

- [x] Inspect agent execution paths, prior run artifacts, and failure signatures for intermittent code-run failures.
- [x] Reproduce the likely failure modes in the local backend runtime.
- [x] Implement the smallest reliable fix in the code execution or pipeline handling path.
- [x] Run targeted verification to prove the failure mode is addressed and note remaining risks.

### Review

- Root causes reproduced in a live `main._run_pipeline(...)` trace:
- Agent code sometimes read `DATA_DIR` / `ARTIFACTS_DIR` from `os.environ`, but the executor only injected Python variables, causing `KeyError`.
- The executor enabled matplotlib constrained layout globally while the prompts encouraged `tight_layout()`, which triggered layout-engine runtime errors for some presenter charts.
- Visualization agents sometimes saved to `/artifacts/...` as if it were a filesystem path; that path is only a public URL, so the file write failed or produced zero collected artifacts.
- The subprocess input path still allowed Windows text-encoding mismatches, so model-generated non-ASCII characters could fail before execution.
- Fixes applied:
- Exported `DATA_DIR` and `ARTIFACTS_DIR` into the subprocess environment as well as Python variables.
- Removed the executor's forced constrained-layout setting, kept `Agg`, and enforced UTF-8 for subprocess input/output.
- Added artifact-required validation for visualization runs so "success with no files" now becomes a retryable error with a concrete path hint.
- Injected live schema into the Hypothesis and Presenter prompts and clarified prompt/tool guidance around local save paths and layout handling.
- Verification:
- Direct executor checks now pass for `os.environ['DATA_DIR']`, `os.environ['ARTIFACTS_DIR']`, `import time`, artifact-required failures, and a colorbar figure that calls `tight_layout()`.
- Two live end-to-end runs of the pricing question were captured. The first showed the original failures before the full fix set. The second run after the fixes completed with `FAILURES 0` and returned three chart artifacts.
- Residual risk: model output can still generate harmless library warnings in `stderr`, but the observed hard failures in the code-execution path were eliminated in the final verification run.

## 2026-04-11 OpenRouter Recheck

- [ ] Run the same targeted 3-question evaluation on OpenRouter `openai/gpt-5.4-mini`.
- [ ] Compare that run with the direct app pipeline behavior on the same provider.
- [ ] Restate the assessment using only OpenRouter-backed evidence.
