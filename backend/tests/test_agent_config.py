import os
import unittest
from unittest.mock import patch

from agents.models.chatcmpl_converter import Converter
from openai.types.chat import ChatCompletionMessage

from agent_defs import config


class AgentConfigTests(unittest.TestCase):
    def test_default_model_is_supported_vertex_model(self):
        self.assertEqual(config.DEFAULT_MODEL_ID, "google/gemini-3.5-flash-lite")

    def test_agent_model_environment_override_is_preserved(self):
        with patch.dict(os.environ, {"AGENT_MODEL": "google/gemini-3.5-flash"}):
            selected_model = os.environ.get("AGENT_MODEL", config.DEFAULT_MODEL_ID)

        self.assertEqual(selected_model, "google/gemini-3.5-flash")

    def test_gemini_thought_signature_survives_tool_call_round_trip(self):
        message = ChatCompletionMessage.model_validate(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "query_database",
                            "arguments": '{"sql":"SELECT 1"}',
                        },
                        "extra_content": {
                            "google": {"thought_signature": "signature-token"}
                        },
                    }
                ],
            }
        )

        output_items = Converter.message_to_output_items(
            message,
            provider_data={"model": config.DEFAULT_MODEL_ID},
        )
        input_items = [item.model_dump(exclude_none=True) for item in output_items]
        messages = Converter.items_to_messages(
            input_items,
            model=config.DEFAULT_MODEL_ID,
        )

        self.assertEqual(
            messages[0]["tool_calls"][0]["extra_content"],
            {"google": {"thought_signature": "signature-token"}},
        )


if __name__ == "__main__":
    unittest.main()
