import os
from statbot import get_codebase_context

codebase_context = get_codebase_context()

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
    f"{codebase_context}\n"
    "=== END CODEBASE CONTEXT ===\n"
)

# Test the demo.py analyze command prompt
filename = "demo.py"
with open(filename, "r", encoding="utf-8", errors='replace') as f:
    lines = f.readlines()
    file_content = "".join([f"{i+1:4d} | {line}" for i, line in enumerate(lines)])

query = (
    f"Focus strictly on the following file for this request. Do NOT hallucinate code from outside this file.\n"
    f"Analyze the following file for bugs. Provide a deep analysis, "
    f"point out the exact line numbers where issues occur, and provide the fixed code:\n\n"
    f"--- {filename} ---\n{file_content}"
)

print("----- GENERATED SYSTEM PROMPT START -----")
print(system_prompt)
print("----- GENERATED SYSTEM PROMPT END -----\n")

print("----- ANALYZE DEMO.PY USER QUERY -----")
print(query)
