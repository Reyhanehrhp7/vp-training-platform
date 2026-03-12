"""Case profile definitions loaded from external prompt files."""

from pathlib import Path


def _load_prompt(relative_path: str) -> str:
    """Load a prompt file relative to this module."""
    prompt_file = Path(__file__).resolve().parent / relative_path
    try:
        return prompt_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return f"Prompt file not found: {prompt_file}"
    except OSError as exc:
        return f"Unable to read prompt file {prompt_file}: {exc}"


CASE_PROFILES = {
    "stephanie_turner": {
        "case_name": "Stephanie Turner - Chronic Cough",
        "chief_complaint": "Coughing is driving her crazy started 3 months ago.",
        "case_prompt": _load_prompt("Stephanie Turner/prompt.txt"),
    },
    "nathalie_rosler": {
        "case_name": "Nathalie Rösler - Acute Dyspnea",
        "chief_complaint": "Since tonight I feel like I can’t breathe properly.",
        "case_prompt": _load_prompt("Nathalie Rösler/prompt.txt"),
    },
    "robert_baley": {
        "case_name": "Robert Baley - Febrile Respiratory Illness",
        "chief_complaint": "Feeling very sick with shaking chills, cough, shortness of breath, and right-sided chest pain.",
        "case_prompt": _load_prompt("Robert Baley/prompt.txt"),
    }
}


DEFAULT_CASE_KEY = next(iter(CASE_PROFILES), None)