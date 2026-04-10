from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent


def load_prompt(name: str) -> str:
    """Load a prompt from a markdown file, stripping YAML frontmatter."""
    text = (_PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8")
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3:]
    return text.strip()
