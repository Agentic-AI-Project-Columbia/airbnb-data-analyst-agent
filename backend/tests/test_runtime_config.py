import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_config import get_cors_origins


class RuntimeConfigTest(unittest.TestCase):
    def test_get_cors_origins_uses_env_value(self) -> None:
        with patch.dict(
            os.environ,
            {"CORS_ALLOW_ORIGINS": "https://frontend.example, https://preview.example"},
            clear=False,
        ):
            self.assertEqual(
                get_cors_origins(),
                ["https://frontend.example", "https://preview.example"],
            )

    def test_get_cors_origins_falls_back_to_local_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                get_cors_origins(),
                ["http://localhost:3000", "http://127.0.0.1:3000"],
            )


if __name__ == "__main__":
    unittest.main()
