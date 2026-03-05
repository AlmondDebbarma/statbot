import os
import sys
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage

load_dotenv() # Loads the .env file automatically

console = Console()

# Configuration for codebase scanning
ALLOWED_EXTENSIONS = {'.py', '.js', '.ts', '.html', '.css', '.json', '.md', '.txt', '.cpp', '.c', '.java'}
IGNORED_DIRS = {'.git', '__pycache__', 'pycache', 'venv', 'node_modules', '.idea', '.vscode', 'env'}

def get_codebase_context() -> str:
    """Recursively scans the current directory and reads all valid source files."""
    context_blocks = []
    
    with console.status("[bold blue]Scanning codebase...", spinner="dots"):
        for root, dirs, files in os.walk("."):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not d.startswith('.')]
            
            for file in files:
                path = Path(root) / file
                if path.suffix in ALLOWED_EXTENSIONS:
                    try:
                        with open(path, "r", encoding="utf-8", errors='replace') as f:
                            content = f.read()
                            context_blocks.append(f"--- File: {path} ---\n{content}\n")
                    except Exception as e:
                        console.print(f"[yellow]Warning: Could not read {path}: {e}[/yellow]")
                        
    return "\n".join(context_blocks)

def main():
    console.print(Panel.fit(
        "[bold green]Welcome to Statbot![/bold green]\n"
        "Your AI Codebase Assistant powered by Groq & LangChain.", 
        border_style="green"
    ))
    
    if not os.environ.get("GROQ_API_KEY"):
        console.print("[bold red]Error: GROQ_API_KEY environment variable is not set.[/bold red]")
        sys.exit(1)
        
    try:
        llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.1)
    except Exception as e:
        console.print(f"[bold red]Error initializing ChatGroq: {e}[/bold red]")
        sys.exit(1)

    codebase_context = get_codebase_context()
    if not codebase_context.strip():
        console.print("[yellow]No supported source files found. Running without codebase context.[/yellow]\n")
        codebase_context = "No local codebase files available."
    else:
        console.print("[green]Codebase loaded successfully![/green]\n")

    system_prompt = (
        "You are Statbot, an expert AI programming assistant.\n\n"
        "*** CRITICAL INSTRUCTION ***\n"
        "1. You MUST ONLY use the provided codebase context to answer questions.\n"
        "2. If a user asks about a file, function, or feature that DOES NOT EXIST in the provided codebase context, you MUST state that you do not see it in the context.\n"
        "3. NEVER guess or hallucinate file names or code that is not explicitly present in the context below.\n"
        "4. When answering questions, ALWAYS cite the exact file name and the line numbers you are referencing.\n"
        "5. If a user asks to prioritize or analyze a specific file, provide deep bug analysis "
        "with code blocks, precise line numbers, and the exact fixed code.\n\n"
        "=== START CODEBASE CONTEXT ===\n"
        "{codebase_context}\n"
        "=== END CODEBASE CONTEXT ===\n"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ])
    
    chain = prompt | llm
    chat_history = []
    
    console.print("[cyan]Tip: Type 'analyze <filename>' for deep bug analysis on a specific file.[/cyan]")
    console.print("[cyan]Type 'exit' or 'quit' to exit.[/cyan]\n")
    
    while True:
        try:
            user_input = Prompt.ask("[bold green]You[/bold green]")
            
            if user_input.strip().lower() in ['exit', 'quit']:
                console.print("[cyan]Goodbye! 👋[/cyan]")
                break
                
            if not user_input.strip():
                continue
                
            query = user_input.strip()
            
            if query.startswith("analyze "):
                # Support custom questions like "analyze demo.py what does this do?"
                parts = query.split(" ", 2)
                filename = parts[1].strip()
                custom_req = parts[2].strip() if len(parts) > 2 else (
                    "Analyze the following file for bugs. Provide a deep analysis, "
                    "point out the exact line numbers where issues occur, and provide the fixed code."
                )
                
                path = Path(filename)
                
                if path.is_file():
                    try:
                        with open(path, "r", encoding="utf-8", errors='replace') as f:
                            file_content = f.read()
                        
                        query = (
                            f"Focus strictly on the following file for this request. Do NOT hallucinate code from outside this file.\n"
                            f"User Request: {custom_req}\n\n"
                            f"--- File: {filename} ---\n{file_content}"
                        )
                        console.print(f"[dim]Analyzing '{filename}'...[/dim]")
                    except Exception as e:
                        console.print(f"[bold red]Error reading file {filename}: {e}[/bold red]")
                        continue
                else:
                    console.print(f"[bold red]Error: File '{filename}' not found.[/bold red]")
                    continue

            with console.status("[bold blue]Statbot is thinking...", spinner="dots"):
                response = chain.invoke({
                    "input": query,
                    "chat_history": chat_history,
                    "codebase_context": codebase_context
                })
                
            chat_history.append(HumanMessage(content=query))
            chat_history.append(response)
            
            console.print(Panel(
                Markdown(response.content), 
                title="[bold blue]Statbot[/bold blue]", 
                border_style="blue", 
                expand=False
            ))
            
        except KeyboardInterrupt:
            console.print("\n[cyan]Goodbye! 👋[/cyan]")
            break
        except Exception as e:
            console.print(f"\n[bold red]An error occurred: {e}[/bold red]")

if __name__ == "__main__":
    main()
