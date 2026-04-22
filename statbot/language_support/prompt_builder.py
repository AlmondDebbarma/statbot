"""
Language-aware prompt builder for Statbot.

Constructs analysis prompts that adapt to the detected language's:
  - paradigm (shapes the mental model)
  - style guide (specific conventions to check)
  - error model (how errors work — exceptions vs. UB vs. return codes)
  - bug patterns (severity-tagged checklist with code examples)
"""

from .detection import LanguageInfo
from .profiles import get_profile


def build_analysis_prompt(
    filename: str,
    file_content: str,
    lang: LanguageInfo,
    custom_request: str | None = None,
) -> str:
    """
    Build a language-tailored analysis prompt.

    If custom_request is provided, it replaces the default analysis instructions
    but language-specific checks are still appended (augmentation, not replacement).
    """
    profile = get_profile(lang.key)

    sections = []

    # --- Header ---
    sections.append(
        f"You are analyzing a **{lang.name}** file (`{filename}`).\n"
        f"Language paradigm: {profile['paradigm']}.\n"
    )

    # --- Main instructions ---
    if custom_request:
        sections.append(
            f"=== USER REQUEST ===\n"
            f"{custom_request}\n\n"
            f"Additionally, apply the following language-specific checks:\n"
        )
    else:
        sections.append(
            f"=== ANALYSIS INSTRUCTIONS ===\n"
            f"Perform an extremely rigorous bug-finding analysis on this {lang.name} code.\n"
            f"You MUST:\n"
            f"1. Perform a step-by-step dry-run of the logical execution flow.\n"
            f"2. Identify all syntax errors, logical bugs, and edge-case failures.\n"
            f"3. Precisely point out the line numbers and explain why each bug occurs.\n"
            f"4. Provide the fully corrected and optimized code.\n"
            f"5. Give the time and space complexity of your solution.\n"
        )

    # --- Style guide section ---
    style = profile['style_guide']
    if style['key_rules']:
        rules_str = '\n'.join(f"  - {r}" for r in style['key_rules'])
        sections.append(
            f"=== STYLE CONVENTIONS ({style['name']}) ===\n"
            f"Check for violations of:\n{rules_str}\n"
        )

    # --- Error model section ---
    err = profile['error_model']
    sections.append(
        f"=== ERROR HANDLING MODEL ({err['type']}) ===\n"
        f"{err['description']}\n"
        f"Check for error-handling anti-patterns specific to this model.\n"
    )

    # --- Bug pattern checklist ---
    patterns = profile['bug_patterns']
    if patterns:
        # Sort by severity: high → medium → low
        severity_order = {'high': 0, 'medium': 1, 'low': 2}
        sorted_patterns = sorted(patterns, key=lambda p: severity_order.get(p['severity'], 3))

        checklist_lines = []
        for p in sorted_patterns:
            checklist_lines.append(
                f"[{p['severity'].upper()}] {p['id']}: {p['name']}\n"
                f"  {p['description']}\n"
                f"  Example:\n"
                f"  ```{lang.fence}\n"
                f"  {p['example']}\n"
                f"  ```\n"
            )
        checklist = '\n'.join(checklist_lines)
        sections.append(
            f"=== {lang.name.upper()} BUG PATTERN CHECKLIST ===\n"
            f"For each pattern below, explicitly state whether it is PRESENT or ABSENT in the code:\n\n"
            f"{checklist}"
        )

    # --- Code to analyze ---
    sections.append(
        f"=== CODE TO ANALYZE ===\n"
        f"File: {filename}\n"
        f"```{lang.fence}\n"
        f"{file_content}\n"
        f"```\n"
    )

    # --- Output format ---
    sections.append(
        f"=== OUTPUT FORMAT ===\n"
        f"1. **Summary**: One-paragraph assessment of overall code quality.\n"
        f"2. **Bug Report**: For each issue found, cite exact line numbers, explain the bug, "
        f"reference the pattern ID if applicable (e.g., {_example_id(patterns)}), and provide the corrected code.\n"
        f"3. **Style Issues**: List {style['name']} violations with line numbers.\n"
        f"4. **Verdict**: Rate the file as CLEAN / MINOR ISSUES / NEEDS FIXES / CRITICAL BUGS.\n"
    )

    return '\n'.join(sections)


def _example_id(patterns: list) -> str:
    """Get an example pattern ID for the output format instructions."""
    if patterns:
        return patterns[0]['id']
    return "BUG001"


def build_iterate_prompt(
    filename: str,
    current_content: str,
    lang: LanguageInfo,
    prev_content: str | None = None,
    round_num: int = 1,
    advanced: bool = False
) -> str:
    """
    Build a Socratic iteration prompt.
    """
    profile = get_profile(lang.key)
    sections = []

    sections.append(f"You are acting as an elite Socratic coding coach for a **{lang.name}** file (`{filename}`).\n")
    
    if advanced:
        sections.append("The user has activated ADVANCED mode. Evaluate for structural perfection, O(n) optimization, language-specific best practices, and elegant abstractions.\n")
    else:
        sections.append("Evaluate this code for bugs, logic errors, and fundamental correctness.\n")

    if round_num == 1:
        sections.append(
            f"=== ROUND 1 INSTRUCTIONS ===\n"
            f"Identify the SINGLE most important issue to fix first (prioritizing fundamental correctness or infinite loops over minor style issues).\n"
            f"Do NOT provide the solution. Do NOT provide line numbers directly. Do NOT write the corrected code.\n"
            f"Provide a 'Where' hint and a 'Glimpse' conceptual hint.\n"
            f"Format strictly as:\n"
            f"ITERATION 1 of {filename}\n"
            f"----------------------\n"
            f"🔍 ONE THING TO FIX: [brief description]\n"
            f"📍 WHERE: [e.g., Around line 14-19. Look at your loop condition.]\n"
            f"💡 GLIMPSE: [Conceptual Socratic hint]\n"
        )
    else:
        sections.append(
            f"=== ROUND {round_num} INSTRUCTIONS (DIFF ANALYSIS) ===\n"
            f"Compare the PREVIOUS CODE to the CURRENT CODE to see what the user changed.\n"
            f"Did the user fix the issue you pointed out in the previous round?\n"
            f"- IF YES: Acknowledge what they did right briefly. Then, identify the NEXT most important issue.\n"
            f"- IF NO: Do not just repeat the hint. Give them a mental trace exercise (e.g., 'Trace this input: arr=[1], target=2').\n"
            f"Do NOT provide the solution. Do NOT write the corrected code.\n"
            f"Format strictly as:\n"
            f"REITERATE — Round {round_num-1} check\n"
            f"-------------------------\n"
            f"✓ [Acknowledgement or trace exercise]\n\n"
            f"[If fixed, next issue details: 🔍 ONE THING TO FIX, 📍 WHERE, 💡 GLIMPSE]\n\n"
            f"ITERATION SCORE\n"
            f"---------------\n"
            f"Round {round_num-1} → Round {round_num}: Correctness +[X]% | Readability +[Y]%\n"
            f"Remaining issues: [N]\n"
            f"Concepts unlocked this session: [concept 1, concept 2]\n"
        )
        
        if not advanced:
            sections.append(
                f"If the code has no major correctness/logic bugs left for a beginner/intermediate level, output:\n"
                f"✓ This code is solid for where you are right now.\n"
                f"What you mastered this session: [...]\n"
                f"What's STILL imperfect (but above your current level): [...]\n"
                f"Run: `statbot iterate {filename} --advanced` to go there now.\n"
            )

    sections.append("=== CODE TO ANALYZE ===")
    if prev_content:
        sections.append(
            f"--- PREVIOUS CODE (Round {round_num-1}) ---\n"
            f"```{lang.fence}\n{prev_content}\n```\n"
        )
    sections.append(
        f"--- CURRENT CODE (Round {round_num}) ---\n"
        f"```{lang.fence}\n{current_content}\n```\n"
    )

    return '\n'.join(sections)
