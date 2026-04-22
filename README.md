# Statbot 🤖

**Statbot** is an AI-powered codebase assistant and Socratic coding coach that runs directly in your terminal. 

Instead of copying and pasting your code into ChatGPT, you can run Statbot directly in your project folder. It will read your entire project instantly and help you hunt down bugs, understand your code, and even coach you through fixing issues yourself without just giving you the answers!

Powered by **Google Gemini 2.5 Flash**, it is lightning-fast and capable of reading massive codebases (up to 200,000 characters of context at once).

---

## 🌟 Features

- **Global CLI:** Run `statbot` from anywhere in your terminal. No need to move files around!
- **Auto-Context:** Automatically reads all the code in your current folder and provides it to the AI.
- **Deep Bug Analysis (`analyze`):** Ask Statbot to do a deep, rigorous bug hunt on a specific file and get precise line numbers and fixed code.
- **Socratic Coach (`iterate`):** Stuck on a problem but want to learn? Statbot will point out the single most important bug, give you a conceptual hint, and refuse to write the code for you. Fix it, type `reiterate`, and it will score your progress!
- **Multi-Language Support:** Understands Python, JavaScript, TypeScript, C++, Java, Rust, HTML, CSS, and more.

---

## 💻 Installation (Beginner Friendly!)

Follow these exact steps to install Statbot on your machine.

### Step 1: Clone or Download this Project
First, download this folder to your computer. Open your terminal (Command Prompt, PowerShell, or Mac Terminal) and navigate inside the folder where you downloaded it.

```bash
cd path/to/statbot
```

### Step 2: Install the Package
Run the following command. This will install Statbot globally on your machine so you can use it anywhere.

```bash
pip install -e .
```
*(The `-e .` means it installs the code from the current folder in "editable" mode).*

### Step 3: Get a Free Gemini API Key
Statbot uses Google's AI, which requires a free API key.
1. Go to [Google AI Studio](https://aistudio.google.com/apikey).
2. Sign in with your Google account.
3. Click **"Create API key"** and copy the long string of letters and numbers it gives you.

### Step 4: Save Your API Key
We need to save this key so Statbot can use it automatically without you having to paste it every time.

**If you are on Windows (PowerShell):**
Run this command, replacing `your_api_key_here` with your actual key:
```powershell
python -c "import os; open(r'C:\Users\' + os.getlogin() + '\.statbot\.env', 'w', encoding='utf-8').write('GEMINI_API_KEY=your_api_key_here\n')"
```

**If you are on Mac/Linux:**
```bash
mkdir -p ~/.statbot
echo "GEMINI_API_KEY=your_api_key_here" > ~/.statbot/.env
```

---

## 🚀 How to Use Statbot

Now that it's installed, you never have to come back to this folder. You can use it on **any** project!

1. Open your terminal.
2. `cd` into the folder of the project you are working on.
3. Type:
   ```bash
   statbot
   ```

Statbot will boot up, scan your project, and give you a `You:` prompt.

### Inside Statbot, you can use these commands:

#### 1. General Chat
Just ask questions! 
- *"Where is the user login logic?"*
- *"Explain how the database connection works."*

#### 2. Deep Analysis
Type `analyze <filename>` to get a rigorous bug report for a specific file.
- `You: analyze app.js`
- `You: analyze main.py why is it crashing on startup?`

#### 3. Socratic Coaching (The best way to learn)
Type `iterate <filename>`. Statbot will look at your file, find the biggest bug, and give you a hint without showing you the answer.
- `You: iterate index.html`

Go to your code editor, try to fix the bug based on the hint, save the file, and then type:
- `You: reiterate`

Statbot will look at what you changed, tell you if you fixed it, give you an Iteration Score, and point out the next issue!

Type `exit` or `quit` to close Statbot when you're done.
