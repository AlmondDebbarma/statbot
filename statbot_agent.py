import os
import sys
import json
import urllib.request
import urllib.error
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

def get_workspace_context(max_files=50):
    context = ""
    ignore_dirs = {'.git', '__pycache__', 'venv', 'env', '.venv', 'node_modules', '.idea', '.vscode'}
    valid_extensions = {'.py', '.js', '.ts', '.html', '.css', '.json', '.md', '.txt', '.cpp', '.c', '.java'}
    
    file_count = 0
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in valid_extensions:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        context += f"\n--- File: {file_path} ---\n```\n{content}\n```\n"
                        file_count += 1
                        if file_count >= max_files:
                            return context, file_count
                except Exception:
                    pass
    return context, file_count

def call_gemini(messages, system_instruction):
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
         console.print("[bold red]Error: GEMINI_API_KEY or GOOGLE_API_KEY not set.[/bold red]")
         sys.exit(1)

    # Use the fastest, cheapest stable model available with highest rate limits
    model_name = "gemini-1.5-flash-8b"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    
    payload = {
        "contents": messages,
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        }
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    
    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            return result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', "No response")
    except urllib.error.HTTPError as e:
        # Fallback to standard gemini-1.5-flash if 8b is heavily rate limited on the user's tier
        try:
            url_fallback = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            req_fallback = urllib.request.Request(url_fallback, data=data, headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req_fallback) as response_fb:
                result = json.loads(response_fb.read().decode('utf-8'))
                return result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', "No response")
        except Exception as fallback_e:
            err_body = e.read().decode('utf-8') if getattr(e, 'read', None) else ""
            return f"**API Error (Primary):** {e.reason} ({e.code})\n\n{err_body}\n\n**Fallback also failed:** {fallback_e}"
    except Exception as e:
        return f"Request Failed: {e}"

def main():
    console.print(Panel("[bold cyan]Statbot Phase 2 - Agentic CLI Assistant[/bold cyan]\nInitializing brain [bold green](Zero-Dependency Native REST Architecture)[/bold green]...", border_style="cyan"))
    
    # Require API key
    if "GEMINI_API_KEY" not in os.environ and "GOOGLE_API_KEY" not in os.environ:
         console.print("[bold yellow]Warning: GEMINI_API_KEY or GOOGLE_API_KEY environment variable not set. Please set it before running.[/bold yellow]")
         sys.exit(1)
    
    with console.status("[bold yellow]Loading codebase context...[/bold yellow]", spinner="dots"):
        workspace_context, file_count = get_workspace_context()
    console.print(f"[bold green]Successfully loaded {file_count} workspace files into context![/bold green]")

    system_instruction = f"""You are Statbot, an elite expert-level AI coding assistant and bug hunter.
You specialize in analyzing code, finding subtle logic flaws, edge cases, and performance bottlenecks.
You evaluate code with extreme precision, trace execution state, and explain issues cleanly.

You have full context awareness of the user's codebase. Here is the current codebase context:
<codebase>
{workspace_context}
</codebase>

Use this codebase context to accurately answer questions, find bugs across files, and understand the project architecture."""

    messages = []
    
    console.print("[bold green]System Ready![/bold green] (Type 'exit' to quit, or 'analyze <filename>' to review a file)")
    
    while True:
        try:
            user_input = console.input("[bold blue]You:[/bold blue] ")
            
            if not user_input.strip():
                continue
                
            if user_input.lower() in ["exit", "quit", "stop", "goodbye"]:
                console.print("Exiting Statbot...")
                break
                
            response_text = ""
                
            # AGENTIC TOOL: File System Analysis Command
            if user_input.lower().startswith("analyze "):
                filename = user_input[8:].strip()
                if not os.path.exists(filename):
                     console.print(f"[red]Error: File '{filename}' not found.[/red]")
                     continue
                
                with console.status(f"[bold yellow]Reading and Analyzing {filename}...[/bold yellow]", spinner="dots"):
                    with open(filename, 'r', encoding='utf-8') as f:
                         file_content = f.read()
                    
                    analysis_prompt = f"""Please perform an extremely rigorous, 100x enhanced bug-finding analysis on this code from '{filename}'.
You MUST:
1. Perform a step-by-step dry-run of the logical execution flow.
2. Identify all syntax errors, logical bugs, and edge-case failures.
3. Precisely point out the line numbers and explain why the bug occurs.
4. Provide the fully corrected and optimized code.
5. Give the time and space complexity of your solution.

Here is the code:
```python
{file_content}
```"""
                    messages.append({'role': 'user', 'parts': [{'text': analysis_prompt}]})
                    response_text = call_gemini(messages, system_instruction)
                    messages.append({'role': 'model', 'parts': [{'text': response_text}]})
            else:
                 # Standard conversation path
                 with console.status("[bold yellow]Thinking...[/bold yellow]", spinner="dots"):
                     messages.append({'role': 'user', 'parts': [{'text': user_input}]})
                     response_text = call_gemini(messages, system_instruction)
                     if not response_text.startswith("**API Error"):
                         messages.append({'role': 'model', 'parts': [{'text': response_text}]})
                     else:
                         messages.pop() # Remove the user message if it failed
            
            # Output using Rich formatting
            console.print(Panel(Markdown(response_text), title="[bold magenta]Statbot[/bold magenta]", border_style="magenta"))
            
        except KeyboardInterrupt:
            console.print("\n[bold red]Exiting gracefully...[/bold red]")
            break
        except Exception as e:
            console.print(f"[bold red]An error occurred: {e}[/bold red]")

if __name__ == "__main__":
    main()
