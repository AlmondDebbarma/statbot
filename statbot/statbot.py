import os
import sys
import time
import json
import urllib.request
import urllib.error
from pathlib import Path

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

# Context budget — Gemini has 250K TPM so we can afford more context than Groq
MAX_CONTEXT_CHARS = 200_000   # ~50K tokens
MAX_FILE_CHARS = 30_000       # Skip individual files larger than ~7.5K tokens
MAX_HISTORY_MESSAGES = 10     # Keep chat history trimmed

# Gemini models — we use a fallback list to bypass free-tier 503 capacity issues
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-pro-latest"
]


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
            # Extract text from Gemini response
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
        if e.code in (429, 503):
            raise RetryableAPIError(f"API busy or limited ({e.code}): {body}")
        return f"**API Error ({e.code}):** {e.reason}\n\n{body[:500]}"
    except urllib.error.URLError as e:
        return f"**Network Error:** {e.reason}"


class RetryableAPIError(Exception):
    """Raised when Gemini returns 429 or 503."""
    pass


# ── Codebase Scanner ──────────────────────────────────────────────────

def get_codebase_context() -> tuple:
    """Recursively scans the current directory and reads all valid source files."""
    context_blocks = []
    total_chars = 0
    file_count = 0
    skipped = []

    with console.status("[bold blue]Scanning codebase...", spinner="dots"):
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith('.')]

            for file in files:
                if file in IGNORED_FILES or file.startswith('.'):
                    continue

                path = Path(root) / file
                if path.suffix not in ALLOWED_EXTENSIONS:
                    continue

                try:
                    size = path.stat().st_size

                    if size > MAX_FILE_CHARS:
                        skipped.append(f"{path} ({size // 1024}KB)")
                        continue

                    if total_chars + size > MAX_CONTEXT_CHARS:
                        skipped.append("... and remaining files (context budget reached)")
                        break

                    with open(path, "r", encoding="utf-8", errors='replace') as f:
                        content = f.read()

                    context_blocks.append(f"--- File: {path} ---\n{content}\n")
                    total_chars += len(content)
                    file_count += 1
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not read {path}: {e}[/yellow]")
            else:
                continue
            break  # Break outer loop if inner loop broke (budget reached)

    if skipped:
        console.print(f"[dim]Skipped {len(skipped)} file(s): too large or budget reached[/dim]")

    return "\n".join(context_blocks), file_count, total_chars


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

    # ── Load codebase ──
    codebase_context, file_count, context_chars = get_codebase_context()
    if not codebase_context.strip():
        console.print("[yellow]No supported source files found. Running without codebase context.[/yellow]\n")
        codebase_context = "No local codebase files available."
    else:
        est_tokens = context_chars // 4
        console.print(f"[green]Codebase loaded: {file_count} files, ~{est_tokens:,} tokens[/green]\n")

    # ── System prompts ──
    system_prompt_text = (
        "You are Statbot, an expert AI programming assistant.\n\n"
        "*** CRITICAL INSTRUCTION ***\n"
        "1. You MUST ONLY use the provided codebase context to answer questions.\n"
        "2. If a user asks about a file, function, or feature that DOES NOT EXIST in the provided codebase context, you MUST state that you do not see it in the context.\n"
        "3. NEVER guess or hallucinate file names or code that is not explicitly present in the context below.\n"
        "4. When answering questions, ALWAYS cite the exact file name and the line numbers you are referencing.\n"
        "5. If a user asks to prioritize or analyze a specific file, provide deep bug analysis "
        "with code blocks, precise line numbers, and the exact fixed code.\n\n"
        "=== START CODEBASE CONTEXT ===\n"
        f"{codebase_context}\n"
        "=== END CODEBASE CONTEXT ===\n"
    )

    # Lightweight system prompt for analyze commands (file is in the user message, not system)
    analyze_system_text = (
        "You are Statbot, an expert AI programming assistant and bug hunter.\n"
        "You are proficient in Python, JavaScript, TypeScript, C, C++, Java, and more.\n"
        "You adapt your analysis to each language's idioms, common pitfalls, and ecosystem.\n"
        "Provide precise line numbers, clear explanations, and corrected code."
    )

    # Gemini uses a list of {"role": "user"/"model", "parts": [{"text": ...}]} messages
    chat_history = []
    is_analyze = False
    iterate_state = {"file": None, "prev_content": None, "round": 0, "advanced": False}

    console.print(f"[cyan]Multi-language support: {get_supported_languages()}[/cyan]")
    console.print("[cyan]Tip: Type 'analyze <filename>' for deep bug analysis on a specific file.[/cyan]")
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

            # Select system prompt
            active_system = analyze_system_text if is_analyze else system_prompt_text

            # Build Gemini message list
            gemini_messages = list(chat_history) + [
                {"role": "user", "parts": [{"text": query}]}
            ]

            # Retry loop with exponential backoff and model fallbacks
            response_text = None
            max_attempts = len(GEMINI_MODELS) * 2  # Try each model twice
            for attempt in range(max_attempts):
                current_model = GEMINI_MODELS[attempt % len(GEMINI_MODELS)]
                try:
                    with console.status(f"[bold blue]Statbot thinking ({current_model})...", spinner="dots"):
                        response_text = call_gemini(gemini_messages, active_system, api_key, current_model)
                    break
                except RetryableAPIError as e:
                    wait = (2 ** (attempt // len(GEMINI_MODELS))) + 1
                    err_msg = str(e).split(':', 1)[0]
                    
                    next_model = GEMINI_MODELS[(attempt + 1) % len(GEMINI_MODELS)]
                    console.print(f"[bold yellow]{err_msg} on {current_model}. Trying {next_model} in {wait}s...[/bold yellow]")
                    time.sleep(wait)

            if response_text is None:
                console.print("[bold red]Failed after 5 retries due to rate limiting.[/bold red]")
                continue

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
