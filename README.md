# Statbot

**Statbot** is an AI-powered codebase assistant and Socratic coding coach that runs in your terminal.

Instead of copying and pasting code into ChatGPT, run Statbot inside your project folder. It reads your code, answers questions about it, hunts down bugs with exact line numbers, and can coach you through fixing issues yourself — without just giving you the answers.

Powered by **Google Gemini 2.5 Flash** (free tier).

---

## Features

- **Smart Context Loading** — Instead of blindly dumping every file at the AI, Statbot scores each file by how relevant it is to your question and only sends the top matches. Saves your daily token quota and keeps answers focused.
- **General Chat** — Ask anything about your codebase. Statbot cites exact file names and line numbers in every answer.
- **Deep Bug Analysis (`analyze`)** — Rigorous bug hunt on a specific file. Get a severity-ranked report with exact line numbers and corrected code.
- **Socratic Coach (`iterate` / `reiterate`)** — Statbot finds the single most important bug, gives you a conceptual hint, and refuses to write the fix for you. Fix it yourself, type `reiterate`, and get an Iteration Score showing your progress.
- **Multi-Language** — Python, JavaScript, TypeScript, C, C++, Java, HTML, CSS, Rust, Go, and more.
- **`.statbotignore`** — Exclude folders and files from context, just like `.gitignore`. Useful for keeping demo files, build artifacts, or the tool's own source out of the AI's view.
- **Model Fallback** — If the primary model hits a rate limit, Statbot silently falls back to `gemini-2.5-flash-lite` without interrupting your session.

---

## Installation

### 1. Clone the project

```bash
git clone https://github.com/AlmondDebbarma/statbot.git
cd statbot
```

### 2. Install globally

```bash
pip install -e .
```

The `-e .` installs from the current folder in editable mode. After this, the `statbot` command is available anywhere on your machine.

### 3. Get a free Gemini API key

1. Go to [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Sign in with your Google account
3. Click **Create API key** and copy it

### 4. Save the key (one-time setup)

**Windows (PowerShell):**
```powershell
python -c "import os; p=os.path.expanduser('~/.statbot'); os.makedirs(p, exist_ok=True); open(p+'/.env','w').write('GEMINI_API_KEY=your_key_here\n')"
```

**Mac / Linux:**
```bash
mkdir -p ~/.statbot
echo "GEMINI_API_KEY=your_key_here" > ~/.statbot/.env
```

Replace `your_key_here` with the key you copied. This file is read automatically every time you run Statbot from any directory.

---

## Usage

Open a terminal, `cd` into any project folder, and run:

```bash
statbot
```

Or point it at a specific directory:

```bash
statbot /path/to/your/project
```

Statbot scans the folder, indexes your files, and gives you a prompt.

### Commands

#### General chat
Just type your question:
```
You: Where is the user authentication logic?
You: Why might this crash on startup?
You: Explain how the database connection pool works.
```
Statbot selects the most relevant files for each question automatically and cites exact file names and line numbers in every answer.

#### Deep bug analysis
```
You: analyze app.py
You: analyze main.js why does the login fail?
```
Performs a full severity-ranked bug report: dry-runs the logic, flags every issue with line numbers, provides the corrected code, and gives a final verdict (CLEAN / MINOR ISSUES / NEEDS FIXES / CRITICAL BUGS).

#### Socratic coaching
```
You: iterate homework.py
```
Statbot finds the biggest bug and gives you a hint — no answer, no line numbers. Fix it in your editor, save, then:
```
You: reiterate
```
Statbot checks what you changed, acknowledges the fix (or gives you a trace exercise if you missed it), and points to the next issue. Includes an Iteration Score each round.

For advanced mode (structural and performance issues, not just correctness):
```
You: iterate homework.py --advanced
```

#### Exit
```
You: exit
```

---

## Excluding files with `.statbotignore`

Create a `.statbotignore` file in the directory you run Statbot from. Syntax is identical to `.gitignore`.

```
# Exclude the statbot source package when running from this repo
statbot/

# Exclude demo files
demo_code.*
demo.py

# Exclude build artifacts
*.egg-info
dist/
build/
```

Lines starting with `#` are comments. Directory patterns end with `/`. File patterns support `*` wildcards.

---

## Free tier limits (at a glance)

| What | Limit |
|---|---|
| Questions per minute | ~9 (enforced by Statbot) |
| Questions per day | ~50 on Flash, ~75 on Flash-Lite |
| Lines of code per query | ~2,000–3,000 (smart-selected) |
| Max single file size | ~400–500 lines |
| Conversation memory | Last 5 exchanges |

All free. No credit card required.

---

## How context selection works

When you ask a question, Statbot scores every indexed file:
- **+10** if the filename contains a keyword from your query
- **+1 per occurrence** (capped at 5) if the content contains a keyword

The top-scoring files are loaded up to the token budget. If your question mentions `auth`, files named `auth.py` or `middleware.js` containing `authenticate` will rank above unrelated files.

When the loaded file set changes between questions (i.e. a different topic), Statbot automatically trims conversation history to the last exchange. This prevents the AI from referencing files it can no longer see.
