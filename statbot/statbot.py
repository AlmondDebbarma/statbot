import os
import re
import sys
import time
import json
import random
import hashlib
import fnmatch
import urllib.request
import urllib.error
from pathlib import Path
from collections import namedtuple

from dotenv import load_dotenv

# Search for .env in multiple locations so the API key works globally:
#   1. Current working directory
#   2. ~/.statbot/.env  (one-time setup, works from anywhere)
#   3. ~/.env
_home = Path.home()
_env_locations = [
    Path.cwd() / ".env",
    _home / ".statbot" / ".env",
    _home / ".env",
]
for _env_path in _env_locations:
    if _env_path.is_file():
        load_dotenv(dotenv_path=_env_path)
        break
else:
    load_dotenv()  # Fallback: let python-dotenv search its default chain

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from statbot.language_support import detect_language, build_analysis_prompt, build_iterate_prompt, get_supported_languages

console = Console()

# ── Configuration ──────────────────────────────────────────────────────
ALLOWED_EXTENSIONS = {'.py', '.js', '.ts', '.html', '.css', '.json', '.md', '.txt', '.cpp', '.c', '.java'}
IGNORED_DIRS = {'.git', '__pycache__', 'pycache', 'venv', 'node_modules', '.idea', '.vscode', 'env',
                'dist', 'build', '.eggs', '*.egg-info'}
IGNORED_FILES = {'.env', 'package-lock.json', 'yarn.lock'}

# Context budget — reduced to stay well within free-tier 250K TPM limit
MAX_CONTEXT_CHARS = 80_000    # ~20K tokens (allows ~12 req/min within TPM)
MAX_FILE_CHARS = 15_000       # ~3.75K tokens per file
MAX_HISTORY_MESSAGES = 10     # Keep chat history trimmed

# Client-side rate limiting — free tier allows ~10 RPM, we stay under 9
MIN_CALL_INTERVAL = 6.5       # Minimum seconds between user queries (not retries)
_last_call_time = 0.0

# Response cache for repeated queries (e.g., re-analyzing same file)
_response_cache = {}
MAX_CACHE_SIZE = 20

# ── Smart file loading ─────────────────────────────────────────────────
FileEntry = namedtuple('FileEntry', ['path', 'content', 'char_count'])

_STOP_WORDS = {
    'a', 'an', 'the', 'is', 'it', 'in', 'on', 'at', 'to', 'for', 'of', 'and',
    'or', 'but', 'not', 'do', 'does', 'did', 'be', 'are', 'was', 'were', 'have',
    'has', 'had', 'will', 'would', 'can', 'could', 'should', 'may', 'might',
    'this', 'that', 'these', 'those', 'i', 'my', 'me', 'we', 'you', 'he', 'she',
    'they', 'what', 'which', 'who', 'how', 'why', 'when', 'where', 'with',
    'from', 'by', 'about', 'up', 'out', 'if', 'then', 'so', 'just', 'all',
}

# Gemini models — only valid, available free-tier models (April 2026)
# Order matters: primary model first, then fallbacks
GEMINI_MODELS = [
    "gemini-2.5-flash",         # Primary — best free-tier model, 1M context
    "gemini-2.5-flash-lite",    # Fast fallback — lightweight, very stable
]
MAX_RETRIES_PER_MODEL = 3     # Retry each model up to 3 times before moving on


# ── Gemini API ─────────────────────────────────────────────────────────

def _get_api_key() -> str:
    """Resolve the Gemini API key from environment."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        console.print(
            "[bold red]Error: GEMINI_API_KEY not found.[/bold red]\n\n"
            "Get your free key:\n"
            "  1. Go to [cyan]https://aistudio.google.com/apikey[/cyan]\n"
            "  2. Click 'Create API key' and copy it\n"
            "  3. Save it once (works globally from any directory):\n\n"
            '  [cyan]echo GEMINI_API_KEY=AIza_your_key > ~/.statbot/.env[/cyan]\n'
        )
        sys.exit(1)
    return key


def _rate_limit():
    """Enforce minimum interval between API calls to stay under RPM limits."""
    global _last_call_time
    elapsed = time.time() - _last_call_time
    if elapsed < MIN_CALL_INTERVAL:
        wait = MIN_CALL_INTERVAL - elapsed
        time.sleep(wait)
    _last_call_time = time.time()


def _cache_key(query: str, system: str) -> str:
    """Create a hash key for caching identical requests."""
    return hashlib.md5((query + system).encode()).hexdigest()


class RateLimitError(Exception):
    """Raised on 429 — quota exhausted for this model, skip to next immediately."""
    pass


class ServerOverloadError(Exception):
    """Raised on 503 — transient server issue, worth retrying with backoff."""
    pass


class FatalAPIError(Exception):
    """Raised on non-retryable errors (400, 401, 403, 404) — skip to next model."""
    pass


def call_gemini(messages: list, system_instruction: str, api_key: str, model_name: str) -> str:
    """Call the Gemini REST API and return the text response."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_name}:generateContent?key={api_key}"
    )

    payload = {
        "contents": messages,
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "generationConfig": {
            "temperature": 0.1,
        },
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            candidates = result.get("candidates", [])
            if not candidates:
                return "No response generated."
            parts = candidates[0].get("content", {}).get("parts", [])
            return "".join(p.get("text", "") for p in parts) or "No response generated."
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8")
        except Exception:
            pass
        if e.code == 429:
            raise RateLimitError(f"Rate limited (429): {body[:200]}")
        if e.code == 503:
            raise ServerOverloadError(f"Server overloaded (503): {body[:200]}")
        if e.code in (400, 401, 403, 404):
            raise FatalAPIError(f"Non-retryable error ({e.code}): {e.reason} — {body[:200]}")
        raise FatalAPIError(f"HTTP {e.code}: {e.reason} — {body[:200]}")
    except urllib.error.URLError as e:
        raise FatalAPIError(f"Network error: {e.reason}")


def call_gemini_with_retry(messages: list, system_instruction: str, api_key: str) -> tuple:
    """Try each model in order. 429 → skip immediately. 503 → retry with backoff.

    Returns:
        (response_text, model_name) on success, or (None, None) on total failure.
    """
    _rate_limit()  # Enforce RPM budget once per user query, not per retry
    for model_idx, model in enumerate(GEMINI_MODELS):
        next_model = GEMINI_MODELS[model_idx + 1] if model_idx + 1 < len(GEMINI_MODELS) else None

        for attempt in range(MAX_RETRIES_PER_MODEL):
            try:
                response = call_gemini(messages, system_instruction, api_key, model)
                return response, model

            except RateLimitError:
                # Quota exhausted — retrying won't help, move on immediately
                if next_model:
                    console.print(
                        f"[dim yellow]{model} rate limited — switching to {next_model}[/dim yellow]"
                    )
                else:
                    console.print(f"[dim yellow]{model} rate limited — no more models to try[/dim yellow]")
                break  # Skip to next model

            except ServerOverloadError:
                # Transient overload — short backoff may help
                wait = (2 ** attempt) + random.uniform(0.5, 1.5)
                remaining = MAX_RETRIES_PER_MODEL - attempt - 1
                if remaining > 0:
                    console.print(
                        f"[dim yellow]{model} overloaded — retrying in {wait:.1f}s[/dim yellow]"
                    )
                    time.sleep(wait)
                else:
                    if next_model:
                        console.print(f"[dim yellow]{model} overloaded — switching to {next_model}[/dim yellow]")
                    break

            except FatalAPIError as e:
                console.print(f"[bold red]✗ {model} error: {str(e)[:120]}[/bold red]")
                break  # Skip remaining retries for this model

    return None, None


# ── Codebase Scanner ──────────────────────────────────────────────────

def _load_ignore_patterns() -> list:
    """Load glob patterns from .statbotignore if present."""
    ignore_file = Path(".statbotignore")
    if not ignore_file.is_file():
        return []
    patterns = []
    for line in ignore_file.read_text(encoding='utf-8', errors='replace').splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            patterns.append(line)
    return patterns


def _is_ignored(path: Path, patterns: list) -> bool:
    """Return True if path matches any .statbotignore pattern."""
    name = path.name
    # Normalise to forward slashes for cross-platform matching
    path_str = str(path).replace('\\', '/')
    for pattern in patterns:
        if fnmatch.fnmatch(name, pattern):
            return True
        if fnmatch.fnmatch(path_str, pattern):
            return True
        # Directory pattern like "statbot/" — match any path component
        if pattern.endswith('/') and pattern.rstrip('/') in path.parts:
            return True
    return False


def build_file_index() -> list:
    """Scan the codebase once and return a list of FileEntry objects.

    Respects IGNORED_DIRS, IGNORED_FILES, .statbotignore, and MAX_FILE_CHARS.
    Does NOT apply MAX_CONTEXT_CHARS — that is enforced at query time.
    """
    index = []
    skipped = []
    ignore_patterns = _load_ignore_patterns()

    with console.status("[bold blue]Scanning codebase...", spinner="dots"):
        for root, dirs, files in os.walk("."):
            dirs[:] = [
                d for d in dirs
                if d not in IGNORED_DIRS
                and not d.startswith('.')
                and not d.endswith('.egg-info')
                and not any(fnmatch.fnmatch(d, p.rstrip('/')) for p in ignore_patterns)
            ]

            for file in files:
                if file in IGNORED_FILES or file.startswith('.'):
                    continue

                path = Path(root) / file
                if path.suffix not in ALLOWED_EXTENSIONS:
                    continue

                if ignore_patterns and _is_ignored(path, ignore_patterns):
                    continue

                try:
                    content = path.read_text(encoding='utf-8', errors='replace')
                    if len(content) > MAX_FILE_CHARS:
                        skipped.append(str(path))
                        continue
                    index.append(FileEntry(path=str(path), content=content, char_count=len(content)))
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not read {path}: {e}[/yellow]")

    if skipped:
        console.print(f"[dim]Skipped {len(skipped)} file(s) — too large[/dim]")

    return index


def select_relevant_files(query: str, file_index: list) -> tuple:
    """Pick the most relevant files for a query using keyword scoring.

    Scores each file by how many query keywords appear in the filename (weight 10)
    and content (weight 1 per occurrence, capped at 5). Returns the top-scoring
    files that fit within MAX_CONTEXT_CHARS. Falls back to index order when no
    keywords match.

    Returns:
        (context_str, loaded_file_count, total_chars, selected_paths)
    """
    if not file_index:
        return "No local codebase files available.", 0, 0, []

    # Extract meaningful keywords from the query
    keywords = set(re.sub(r'[^\w]', ' ', query.lower()).split()) - _STOP_WORDS

    if keywords:
        scored = []
        for entry in file_index:
            score = 0
            content_lower = entry.content.lower()
            name_lower = Path(entry.path).name.lower()
            for kw in keywords:
                if kw in name_lower:
                    score += 10
                score += min(content_lower.count(kw), 5)
            scored.append((score, entry))
        scored.sort(key=lambda x: -x[0])
        ordered = [e for _, e in scored]
    else:
        ordered = list(file_index)  # No keywords — use index order

    context_blocks = []
    selected_paths = []
    total = 0

    for entry in ordered:
        if total + entry.char_count > MAX_CONTEXT_CHARS:
            break
        context_blocks.append(f"--- File: {entry.path} ---\n{entry.content}\n")
        selected_paths.append(Path(entry.path).name)
        total += entry.char_count

    # If the top-scored files filled the budget but nothing was included, load first file
    if not context_blocks and file_index:
        entry = file_index[0]
        context_blocks.append(f"--- File: {entry.path} ---\n{entry.content}\n")
        selected_paths.append(Path(entry.path).name)
        total = entry.char_count

    return "\n".join(context_blocks), len(context_blocks), total, selected_paths


# ── Main ──────────────────────────────────────────────────────────────

def main():
    # Handle optional path argument: statbot [path]
    target_dir = None
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in ("-h", "--help"):
            console.print(
                "[bold green]Statbot[/bold green] — AI Codebase Assistant\n\n"
                "[bold]Usage:[/bold]\n"
                "  statbot              Analyze the current directory\n"
                "  statbot [path]       Analyze a specific project directory\n"
                "  statbot --help       Show this help message\n\n"
                "[bold]Inside Statbot:[/bold]\n"
                "  analyze <file>       Deep bug analysis on a specific file\n"
                "  exit / quit          Exit Statbot\n\n"
                "[bold]Setup:[/bold]\n"
                "  Create [cyan]~/.statbot/.env[/cyan] with your API key:\n"
                "  [dim]GEMINI_API_KEY=AIza_your_key_here[/dim]"
            )
            sys.exit(0)
        target_dir = Path(arg).resolve()
        if not target_dir.is_dir():
            console.print(f"[bold red]Error: '{arg}' is not a valid directory.[/bold red]")
            sys.exit(1)

    # Change to target directory so all file operations work relative to the project
    if target_dir:
        os.chdir(target_dir)

    console.print(Panel.fit(
        "[bold green]Welcome to Statbot![/bold green]\n"
        "Your AI Codebase Assistant powered by Gemini.",
        border_style="green"
    ))
    console.print(f"[dim]Working directory: {Path.cwd()}[/dim]\n")

    api_key = _get_api_key()

    # ── Index codebase (once at startup) ──
    file_index = build_file_index()
    if not file_index:
        console.print("[yellow]No supported source files found. Running without codebase context.[/yellow]\n")
    else:
        ignore_note = " (.statbotignore active)" if Path(".statbotignore").is_file() else ""
        console.print(f"[green]Indexed {len(file_index)} files{ignore_note} — context selected per query[/green]\n")

    # Lightweight system prompt for analyze/iterate commands (file content is in the user message)
    analyze_system_text = (
        "You are Statbot, an expert AI programming assistant and bug hunter.\n"
        "You are proficient in Python, JavaScript, TypeScript, C, C++, Java, and more.\n"
        "You adapt your analysis to each language's idioms, common pitfalls, and ecosystem.\n"
        "Provide precise line numbers, clear explanations, and corrected code."
    )

    _SYSTEM_PREFIX = (
        "You are Statbot, an expert AI programming assistant.\n\n"
        "*** CRITICAL INSTRUCTIONS ***\n"
        "1. ONLY use the files listed in the current codebase context below to answer questions.\n"
        "2. If a file, function, or feature is NOT in the current context, say so explicitly.\n"
        "3. NEVER hallucinate file names or code that is not present in the current context.\n"
        "4. Always cite the exact file name and line numbers when referencing code.\n"
        "5. Each query loads a FRESH set of relevant files. NEVER refer to files from earlier "
        "in the conversation unless they appear in the CURRENT context below.\n\n"
    )

    # Gemini uses a list of {"role": "user"/"model", "parts": [{"text": ...}]} messages
    chat_history = []
    is_analyze = False
    iterate_state = {"file": None, "prev_content": None, "round": 0, "advanced": False}
    last_context_files: set = set()  # Track previous query's file set for history trimming

    console.print(f"[cyan]Multi-language support: {get_supported_languages()}[/cyan]")
    console.print("[cyan]Tip: Type 'analyze <filename>' for deep bug analysis on a specific file.[/cyan]")
    console.print("[cyan]Tip: Create .statbotignore to exclude folders/files from context.[/cyan]")
    console.print("[cyan]Type 'exit' or 'quit' to exit.[/cyan]\n")

    while True:
        try:
            user_input = Prompt.ask("[bold green]You[/bold green]")

            if user_input.strip().lower() in ['exit', 'quit']:
                console.print("[cyan]Goodbye![/cyan]")
                break

            if not user_input.strip():
                continue

            query = user_input.strip()

            if query.startswith("analyze "):
                # Support custom questions like "analyze demo.py what does this do?"
                parts = query.split(" ", 2)
                filename = parts[1].strip()
                custom_req = parts[2].strip() if len(parts) > 2 else None

                path = Path(filename)

                if path.is_file():
                    try:
                        with open(path, "r", encoding="utf-8", errors='replace') as f:
                            file_content = f.read()

                        lang = detect_language(str(path))
                        console.print(f"[dim]Detected language: {lang.name} | Analyzing '{filename}'...[/dim]")
                        query = build_analysis_prompt(filename, file_content, lang, custom_request=custom_req)
                        is_analyze = True
                    except Exception as e:
                        console.print(f"[bold red]Error reading file {filename}: {e}[/bold red]")
                        continue
                else:
                    console.print(f"[bold red]Error: File '{filename}' not found.[/bold red]")
                    continue
            
            elif query.startswith("iterate "):
                parts = query.split(" ")
                filename = parts[1].strip()
                advanced = "--advanced" in parts
                
                path = Path(filename)
                if path.is_file():
                    try:
                        with open(path, "r", encoding="utf-8", errors='replace') as f:
                            file_content = f.read()
                            
                        lang = detect_language(str(path))
                        console.print(f"[dim]Detected language: {lang.name} | Socratic Iteration '{filename}' (Round 1)...[/dim]")
                        
                        iterate_state = {"file": str(path), "prev_content": file_content, "round": 1, "advanced": advanced}
                        
                        query = build_iterate_prompt(
                            filename=filename,
                            current_content=file_content,
                            lang=lang,
                            round_num=1,
                            advanced=advanced
                        )
                        is_analyze = True
                        chat_history = []  # Reset history for a clean iteration session
                    except Exception as e:
                        console.print(f"[bold red]Error reading file {filename}: {e}[/bold red]")
                        continue
                else:
                    console.print(f"[bold red]Error: File '{filename}' not found.[/bold red]")
                    continue

            elif query == "reiterate":
                if not iterate_state["file"]:
                    console.print("[bold red]Error: No active iteration. Start with 'iterate <filename>' first.[/bold red]")
                    continue
                    
                path = Path(iterate_state["file"])
                if path.is_file():
                    try:
                        with open(path, "r", encoding="utf-8", errors='replace') as f:
                            file_content = f.read()
                            
                        iterate_state["round"] += 1
                        lang = detect_language(str(path))
                        
                        console.print(f"[dim]Socratic Iteration '{path.name}' (Round {iterate_state['round']})...[/dim]")
                        
                        query = build_iterate_prompt(
                            filename=path.name,
                            current_content=file_content,
                            lang=lang,
                            prev_content=iterate_state["prev_content"],
                            round_num=iterate_state["round"],
                            advanced=iterate_state["advanced"]
                        )
                        
                        iterate_state["prev_content"] = file_content
                        is_analyze = True
                    except Exception as e:
                        console.print(f"[bold red]Error reading file {path.name}: {e}[/bold red]")
                        continue
                else:
                    console.print(f"[bold red]Error: File '{iterate_state['file']}' not found.[/bold red]")
                    continue

            else:
                is_analyze = False

            # Select system prompt — analyze uses a fixed prompt; chat builds context per query
            if is_analyze:
                active_system = analyze_system_text
                last_context_files = set()  # Reset so next chat query starts fresh
            else:
                relevant_context, loaded_count, loaded_chars, selected_names = \
                    select_relevant_files(query, file_index)

                current_context_files = set(selected_names)

                # If the file set changed from the previous turn, trim history to the last
                # one exchange only. This prevents the AI from referencing files it can no
                # longer see (the previous context is gone — keeping old history causes it
                # to hallucinate or contradict itself).
                if last_context_files and current_context_files != last_context_files:
                    if chat_history:
                        chat_history = chat_history[-2:]  # Keep last user+model pair only
                        console.print("[dim]Context shifted — conversation trimmed to last exchange[/dim]")

                last_context_files = current_context_files

                if loaded_count > 0:
                    names_str = ", ".join(selected_names[:5])
                    if len(selected_names) > 5:
                        names_str += f" +{len(selected_names) - 5} more"
                    console.print(
                        f"[dim]Context: {loaded_count} file(s) · ~{loaded_chars // 4:,} tokens "
                        f"({names_str})[/dim]"
                    )

                active_system = (
                    _SYSTEM_PREFIX
                    + "=== START CODEBASE CONTEXT ===\n"
                    + relevant_context
                    + "\n=== END CODEBASE CONTEXT ===\n"
                )

            # Build Gemini message list
            gemini_messages = list(chat_history) + [
                {"role": "user", "parts": [{"text": query}]}
            ]

            # Check cache for identical queries (analyze commands)
            cache_k = _cache_key(query, active_system)
            if cache_k in _response_cache:
                response_text = _response_cache[cache_k]
                console.print("[dim green]✓ Cached response (no API call needed)[/dim green]")
            else:
                # Smart retry with model fallback — spinner gives live feedback
                with console.status(
                    "[bold blue]Thinking...[/bold blue]",
                    spinner="dots"
                ):
                    response_text, used_model = call_gemini_with_retry(
                        gemini_messages, active_system, api_key
                    )

                if response_text is None:
                    console.print(
                        "[bold red]All models failed. Possible causes:[/bold red]\n"
                        "  • Free-tier rate limits exceeded (wait 1 minute)\n"
                        "  • Invalid API key (check your .env file)\n"
                        "  • Network connectivity issue"
                    )
                    continue

                # Cache the successful response
                if len(_response_cache) >= MAX_CACHE_SIZE:
                    oldest = next(iter(_response_cache))
                    del _response_cache[oldest]
                _response_cache[cache_k] = response_text

            # Append to history (Gemini format)
            chat_history.append({"role": "user", "parts": [{"text": query}]})
            chat_history.append({"role": "model", "parts": [{"text": response_text}]})

            # Trim history to prevent token buildup
            if len(chat_history) > MAX_HISTORY_MESSAGES:
                chat_history = chat_history[-MAX_HISTORY_MESSAGES:]

            console.print(Panel(
                Markdown(response_text),
                title="[bold blue]Statbot[/bold blue]",
                border_style="blue",
                expand=False
            ))

        except (KeyboardInterrupt, EOFError):
            console.print("\n[cyan]Goodbye![/cyan]")
            break
        except Exception as e:
            console.print(f"\n[bold red]An error occurred: {str(e)[:500]}[/bold red]")

if __name__ == "__main__":
    main()
