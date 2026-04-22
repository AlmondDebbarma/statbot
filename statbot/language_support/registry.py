"""
Extension → language key mapping.

This is intentionally thin — a flat lookup table that's easy to extend.
Adding a language here is step 1; step 2 is adding a profile in profiles.py.
"""

EXTENSION_MAP = {
    # Python
    '.py': 'python', '.pyw': 'python', '.pyi': 'python',
    # JavaScript family
    '.js': 'javascript', '.jsx': 'javascript', '.mjs': 'javascript', '.cjs': 'javascript',
    # TypeScript family
    '.ts': 'typescript', '.tsx': 'typescript',
    # C
    '.c': 'c',
    # C++ 
    '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp', '.hpp': 'cpp', '.hxx': 'cpp',
    # Ambiguous — triggers content-based disambiguation
    '.h': 'c_or_cpp',
    # Java
    '.java': 'java',
    # Web
    '.html': 'html', '.htm': 'html',
    '.css': 'css', '.scss': 'css', '.less': 'css',
    # Data / Config
    '.json': 'json',
    '.yaml': 'yaml', '.yml': 'yaml',
    '.toml': 'toml',
    '.xml': 'xml',
    # Systems
    '.rs': 'rust',
    '.go': 'go',
    # Shell
    '.sh': 'bash', '.bash': 'bash',
    # Docs
    '.md': 'markdown',
    '.txt': 'plaintext',
}

# Extensionless files mapped by exact filename
FILENAME_MAP = {
    'Makefile':        'makefile',
    'makefile':        'makefile',
    'Dockerfile':      'dockerfile',
    'Jenkinsfile':     'groovy',
    'Vagrantfile':     'ruby',
    'CMakeLists.txt':  'cmake',
    '.gitignore':      'gitignore',
    '.env':            'dotenv',
}

# Shebang substrings → language key
SHEBANG_MAP = {
    'python': 'python',
    'node':   'javascript',
    'bash':   'bash',
    'sh':     'bash',
    'ruby':   'ruby',
    'perl':   'perl',
    'php':    'php',
}
