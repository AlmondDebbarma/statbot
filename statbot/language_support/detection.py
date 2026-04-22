"""
Multi-tier language detection engine.

Fallback chain:
  1. File extension (normalized, handles .test.js / .PY)
  2. Known filenames (Makefile, Dockerfile, etc.)
  3. Shebang line (#!/usr/bin/env python3)
  4. Content heuristics (first 30 lines)
  5. Generic fallback
"""

import os
from collections import namedtuple

from .registry import EXTENSION_MAP, FILENAME_MAP, SHEBANG_MAP

LanguageInfo = namedtuple('LanguageInfo', ['key', 'name', 'fence'])

# Mapping from language key to (display name, markdown fence)
_LANG_DISPLAY = {
    'python':      ('Python',      'python'),
    'javascript':  ('JavaScript',  'javascript'),
    'typescript':  ('TypeScript',  'typescript'),
    'c':           ('C',           'c'),
    'cpp':         ('C++',         'cpp'),
    'java':        ('Java',        'java'),
    'html':        ('HTML',        'html'),
    'css':         ('CSS',         'css'),
    'json':        ('JSON',        'json'),
    'yaml':        ('YAML',        'yaml'),
    'toml':        ('TOML',        'toml'),
    'xml':         ('XML',         'xml'),
    'rust':        ('Rust',        'rust'),
    'go':          ('Go',          'go'),
    'bash':        ('Bash',        'bash'),
    'markdown':    ('Markdown',    'markdown'),
    'plaintext':   ('Plain Text',  'text'),
    'makefile':    ('Makefile',    'makefile'),
    'dockerfile':  ('Dockerfile',  'dockerfile'),
    'groovy':      ('Groovy',      'groovy'),
    'ruby':        ('Ruby',        'ruby'),
    'perl':        ('Perl',        'perl'),
    'php':         ('PHP',         'php'),
    'cmake':       ('CMake',       'cmake'),
    'gitignore':   ('Gitignore',   'text'),
    'dotenv':      ('Dotenv',      'text'),
    'kotlin':      ('Kotlin',      'kotlin'),
    'scala':       ('Scala',       'scala'),
    '_generic':    ('Unknown',     'text'),
}


def _make_info(key: str) -> LanguageInfo:
    """Create a LanguageInfo from a language key."""
    name, fence = _LANG_DISPLAY.get(key, (key.title(), key))
    return LanguageInfo(key=key, name=name, fence=fence)


def _extract_extension(filepath: str) -> str:
    """
    Extract the effective extension from a filepath.
    Handles case normalization and double extensions like .test.js, .spec.ts.
    """
    basename = os.path.basename(filepath)
    # Handle double extensions - strip .test. / .spec. / .min. prefixes
    strip_prefixes = ['.test', '.spec', '.min', '.d']
    
    name, ext = os.path.splitext(basename)
    ext = ext.lower()
    
    # Check if this is a double extension case
    if ext and name:
        _, inner_ext = os.path.splitext(name)
        if inner_ext.lower() in [p for p in strip_prefixes]:
            return ext  # Return the outer extension (.js from .test.js)
    
    return ext


def _detect_by_extension(filepath: str) -> str | None:
    """Tier 1: Extension-based detection."""
    ext = _extract_extension(filepath)
    if ext and ext in EXTENSION_MAP:
        return EXTENSION_MAP[ext]
    return None


def _detect_by_filename(filepath: str) -> str | None:
    """Tier 2: Known filename detection (Makefile, Dockerfile, etc.)."""
    basename = os.path.basename(filepath)
    return FILENAME_MAP.get(basename)


def _detect_by_shebang(filepath: str) -> str | None:
    """Tier 3: Shebang line detection."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            first_line = f.readline(512).strip()
        
        if first_line.startswith('#!'):
            shebang = first_line.lower()
            for keyword, lang_key in SHEBANG_MAP.items():
                if keyword in shebang:
                    return lang_key
    except (OSError, IOError):
        pass
    return None


def _detect_by_content(filepath: str) -> str | None:
    """Tier 4: Content heuristic detection (first 30 lines)."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = []
            for i, line in enumerate(f):
                if i >= 30:
                    break
                lines.append(line)
        
        content = ''.join(lines)
        
        # C/C++ includes
        if '#include <' in content or '#include "' in content:
            return _disambiguate_c_cpp(content)
        
        # JavaScript / JSX
        if 'import React' in content or 'export default' in content or 'require(' in content:
            return 'javascript'
        
        # Go
        if 'package main' in content or 'func main()' in content:
            return 'go'
        
        # Rust
        if 'fn main()' in content or 'let mut ' in content:
            return 'rust'
        
        # Java
        if 'public class ' in content or 'public static void main' in content:
            return 'java'
        
        # Python
        if ('def ' in content and 'import ' in content) or 'if __name__' in content:
            return 'python'
        
        # HTML
        if '<!DOCTYPE' in content.upper() or '<html' in content.lower():
            return 'html'
        
    except (OSError, IOError):
        pass
    return None


def _disambiguate_c_cpp(content: str) -> str:
    """Resolve .h ambiguity: look for C++ indicators in content."""
    cpp_signals = [
        'class ', 'namespace ', 'template', 'std::', 'public:', 'private:',
        'protected:', 'virtual ', 'cout', 'cin', 'endl', 'vector<',
        'string ', 'iostream', 'using namespace', '#include <string>',
        '#include <vector>', '#include <iostream>',
    ]
    for signal in cpp_signals:
        if signal in content:
            return 'cpp'
    return 'c'


def detect_language(filepath: str) -> LanguageInfo:
    """
    Detect the programming language of a file using a multi-tier fallback chain.
    
    Chain: extension → known filename → shebang → content heuristics → generic
    
    Returns a LanguageInfo namedtuple with (key, name, fence).
    """
    # Tier 1: Extension
    result = _detect_by_extension(filepath)
    
    # Handle ambiguous .h files
    if result == 'c_or_cpp':
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read(4096)
            result = _disambiguate_c_cpp(content)
        except (OSError, IOError):
            result = 'c'  # Default .h to C if we can't read it
    
    if result:
        return _make_info(result)
    
    # Tier 2: Known filename
    result = _detect_by_filename(filepath)
    if result:
        return _make_info(result)
    
    # Tier 3: Shebang
    result = _detect_by_shebang(filepath)
    if result:
        return _make_info(result)
    
    # Tier 4: Content heuristics
    result = _detect_by_content(filepath)
    if result:
        return _make_info(result)
    
    # Tier 5: Generic fallback
    return _make_info('_generic')
