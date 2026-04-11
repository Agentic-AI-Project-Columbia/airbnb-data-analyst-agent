import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline import build_presenter_input, clean_final_answer, safe_truncate


class PipelineHelpersTest(unittest.TestCase):
    def test_safe_truncate_adds_suffix_when_needed(self) -> None:
        truncated = safe_truncate("abcdefghij", limit=5)
        self.assertEqual(truncated, "abcde\n... (5 chars truncated)")

    def test_clean_final_answer_removes_python_block_and_bare_filename(self) -> None:
        raw = "## Summary\n```python\nprint('hello')\n```\nSaved chart.png\nFinal insight."
        cleaned = clean_final_answer(raw)

        self.assertNotIn("```python", cleaned)
        self.assertNotIn("chart.png", cleaned)
        self.assertIn("Final insight.", cleaned)

    def test_build_presenter_input_includes_existing_chart_context(self) -> None:
        prompt = build_presenter_input(
            "Which borough is priciest?",
            "collector output",
            "analyst output",
            "hypothesis output",
            existing_chart_paths=["/artifacts/run-1/chart.png"],
        )

        self.assertIn("Which borough is priciest?", prompt)
        self.assertIn("/artifacts/run-1/chart.png", prompt)
        self.assertIn("Do NOT recreate these.", prompt)


if __name__ == "__main__":
    unittest.main()
