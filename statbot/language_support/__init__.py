"""
Language Support Module for Statbot.

Public API:
    detect_language(filepath)       → LanguageInfo namedtuple
    build_analysis_prompt(...)      → str (ready-to-send prompt)
    get_supported_languages()       → str (formatted list for CLI help)
"""

from .detection import detect_language
from .prompt_builder import build_analysis_prompt, build_iterate_prompt

from .registry import EXTENSION_MAP

def get_supported_languages() -> str:
    """Returns a formatted string listing supported languages for CLI display."""
    # Collect unique language names
    seen = set()
    languages = []
    for lang_key in EXTENSION_MAP.values():
        if lang_key not in seen and lang_key != 'c_or_cpp':
            seen.add(lang_key)
            languages.append(lang_key)
    return ", ".join(sorted(languages))
