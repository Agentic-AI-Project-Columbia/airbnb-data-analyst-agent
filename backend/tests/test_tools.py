import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class ToolingTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name) / "data"
        self.artifacts_dir = Path(self.temp_dir.name) / "artifacts"
        self.data_dir.mkdir()
        self.artifacts_dir.mkdir()
        self._write_sample_csvs(self.data_dir)

        self.env_patch = patch.dict(
            os.environ,
            {
                "DATA_DIR": str(self.data_dir),
                "ARTIFACTS_DIR": str(self.artifacts_dir),
            },
            clear=False,
        )
        self.env_patch.start()

        import tools.code_executor as code_executor
        import tools.sql_runner as sql_runner

        self.code_executor = importlib.reload(code_executor)
        self.sql_runner = importlib.reload(sql_runner)

    def tearDown(self) -> None:
        connection = getattr(self.sql_runner, "_con", None)
        if connection is not None:
            connection.close()
            self.sql_runner._con = None
        self.env_patch.stop()
        self.temp_dir.cleanup()

    def test_run_sql_reports_truncation_metadata(self) -> None:
        payload = json.loads(
            self.sql_runner.run_sql(
                "SELECT id, name FROM listings ORDER BY id",
                max_rows=1,
            )
        )

        self.assertEqual(payload["row_count"], 2)
        self.assertEqual(payload["returned_row_count"], 1)
        self.assertTrue(payload["truncated"])
        self.assertEqual(payload["data"][0]["id"], 1)

    def test_run_sql_blocks_write_queries(self) -> None:
        payload = json.loads(
            self.sql_runner.run_sql("INSERT INTO listings VALUES (3, 'Bad')")
        )

        self.assertEqual(payload["error"], "Only SELECT queries are allowed.")

    def test_execute_python_blocks_disallowed_imports(self) -> None:
        payload = json.loads(self.code_executor.execute_python("import socket"))

        self.assertEqual(payload["exit_code"], 1)
        self.assertIn("Disallowed imports: socket", payload["stderr"])

    def test_execute_python_collects_chart_artifact(self) -> None:
        code = (
            "import matplotlib.pyplot as plt\n"
            "plt.plot([1, 2, 3], [3, 2, 5])\n"
            "plt.title('Demo Chart')\n"
        )
        payload = json.loads(
            self.code_executor.execute_python(code, require_artifacts=True)
        )

        self.assertEqual(payload["exit_code"], 0)
        self.assertGreaterEqual(len(payload["artifacts"]), 1)
        self.assertTrue(payload["artifacts"][0]["path"].startswith("/artifacts/"))

    @staticmethod
    def _write_sample_csvs(data_dir: Path) -> None:
        (data_dir / "listings.csv").write_text(
            "\n".join(
                [
                    "id,name,host_id,neighbourhood_cleansed,room_type,price,review_scores_rating,number_of_reviews,host_is_superhost",
                    '1,Loft,10,Chelsea,Entire home/apt,$150.00,4.8,12,t',
                    '2,Room,11,Harlem,Private room,$80.00,4.5,5,f',
                ]
            ),
            encoding="utf-8",
        )
        (data_dir / "reviews.csv").write_text(
            "\n".join(
                [
                    "id,listing_id,date,reviewer_id,comments",
                    '100,1,2024-01-01,9001,"Great stay"',
                    '101,2,2024-01-02,9002,"Clean room"',
                ]
            ),
            encoding="utf-8",
        )
        (data_dir / "neighbourhoods.csv").write_text(
            "\n".join(
                [
                    "neighbourhood,neighbourhood_group",
                    "Chelsea,Manhattan",
                    "Harlem,Manhattan",
                ]
            ),
            encoding="utf-8",
        )


if __name__ == "__main__":
    unittest.main()
