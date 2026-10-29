from pathlib import Path

SRC_DIR = Path(__file__).parent

# Go up one level to the root, then into the 'prompts' folder
PROMPTS_DIR = SRC_DIR.parent / "prompts"

def load_prompt(filename: str) -> str:
    """Loads a prompt from the prompts directory."""
    filepath = PROMPTS_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Prompt file not found: {filepath}")
    return filepath.read_text(encoding="utf-8")