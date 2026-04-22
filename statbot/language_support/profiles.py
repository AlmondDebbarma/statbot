"""
Per-language analysis profiles.

Each profile contains:
  - paradigm: how to think about this language
  - style_guide: conventions to check
  - error_model: how errors work in this language
  - bug_patterns: severity-tagged common pitfalls with code examples
"""


def get_profile(language_key: str) -> dict:
    """Return the analysis profile for a language key. Falls back to _generic."""
    return PROFILES.get(language_key, PROFILES['_generic'])


# ---------------------------------------------------------------------------
# PYTHON
# ---------------------------------------------------------------------------
_PYTHON = {
    'paradigm': 'dynamic, interpreted, garbage-collected, multi-paradigm',

    'style_guide': {
        'name': 'PEP 8',
        'key_rules': [
            '4-space indentation, no tabs',
            'snake_case for functions/variables, PascalCase for classes',
            'Max line length 79 (code) / 72 (docstrings)',
            'Prefer f-strings over .format() in Python 3.6+',
            'Use type hints for function signatures',
            'Imports at top of file, grouped: stdlib → third-party → local',
        ],
    },

    'error_model': {
        'type': 'exceptions',
        'description': (
            'Python uses try/except for error handling. '
            'Bare `except:` catches everything including SystemExit and '
            'KeyboardInterrupt — almost always a bug. '
            'Use `except Exception as e:` instead. '
            'Context managers (with statement) should be used for resource cleanup.'
        ),
    },

    'ecosystem': {
        'package_manager': 'pip / poetry',
        'common_frameworks': 'Django, Flask, FastAPI, pytest',
        'import_style': 'from module import name',
    },

    'bug_patterns': [
        {
            'id': 'PY001', 'severity': 'high',
            'name': 'Mutable default argument',
            'description': 'A mutable object (list, dict, set) used as a default parameter is shared across all calls.',
            'example': (
                '# BUG\n'
                'def add(item, items=[]):\n'
                '    items.append(item)\n'
                '    return items\n\n'
                '# FIX\n'
                'def add(item, items=None):\n'
                '    if items is None:\n'
                '        items = []\n'
                '    items.append(item)\n'
                '    return items'
            ),
        },
        {
            'id': 'PY002', 'severity': 'high',
            'name': 'Bare except clause',
            'description': 'Catches SystemExit, KeyboardInterrupt, GeneratorExit — hides real errors.',
            'example': (
                '# BUG\n'
                'try: risky()\n'
                'except: pass\n\n'
                '# FIX\n'
                'try: risky()\n'
                'except Exception as e: log(e)'
            ),
        },
        {
            'id': 'PY003', 'severity': 'medium',
            'name': 'Late binding closure in loop',
            'description': 'Lambda/function in a loop captures the variable by reference. All closures see the final value.',
            'example': (
                '# BUG — all return 4\n'
                'funcs = [lambda: i for i in range(5)]\n\n'
                '# FIX\n'
                'funcs = [lambda i=i: i for i in range(5)]'
            ),
        },
        {
            'id': 'PY004', 'severity': 'medium',
            'name': 'Off-by-one in range/slicing',
            'description': 'range(n) stops at n-1. Forgetting this causes missing last element or IndexError.',
            'example': (
                '# BUG — misses last item\n'
                'for i in range(len(arr) - 1): process(arr[i])\n\n'
                '# FIX\n'
                'for i in range(len(arr)): process(arr[i])\n'
                '# BETTER\n'
                'for item in arr: process(item)'
            ),
        },
        {
            'id': 'PY005', 'severity': 'medium',
            'name': 'Unintended global state mutation',
            'description': 'Modifying module-level mutable objects creates hidden state coupling between functions.',
            'example': (
                '# BUG\n'
                'cache = {}\n'
                'def store(k, v): cache[k] = v  # module-level mutation\n\n'
                '# FIX: use a class or pass explicitly\n'
                'class Store:\n'
                '    def __init__(self): self.cache = {}\n'
                '    def store(self, k, v): self.cache[k] = v'
            ),
        },
        {
            'id': 'PY006', 'severity': 'low',
            'name': 'Using type() instead of isinstance()',
            'description': 'type() does not account for inheritance. isinstance() is almost always preferred.',
            'example': (
                '# BAD\n'
                'if type(x) == int: ...\n\n'
                '# GOOD\n'
                'if isinstance(x, int): ...'
            ),
        },
    ],
}

# ---------------------------------------------------------------------------
# JAVASCRIPT
# ---------------------------------------------------------------------------
_JAVASCRIPT = {
    'paradigm': 'dynamic, interpreted, event-driven, prototype-based, single-threaded',

    'style_guide': {
        'name': 'Airbnb JavaScript Style Guide',
        'key_rules': [
            'Prefer const over let; never use var',
            'Always use === and !== (strict equality)',
            'Use arrow functions for callbacks',
            'Semicolons required',
            'Use template literals instead of string concatenation',
            'Destructure objects and arrays where possible',
        ],
    },

    'error_model': {
        'type': 'exceptions + undefined + NaN propagation',
        'description': (
            'JS uses try/catch but also has silent failure modes: '
            'accessing properties on undefined/null, NaN propagation through '
            'arithmetic, and implicit type coercion. Unhandled Promise rejections '
            'crash Node.js processes. Always use .catch() or try/catch with async/await.'
        ),
    },

    'ecosystem': {
        'package_manager': 'npm / yarn / pnpm',
        'common_frameworks': 'React, Express, Next.js, Vue',
        'import_style': "import x from 'module' (ESM) / const x = require('module') (CJS)",
    },

    'bug_patterns': [
        {
            'id': 'JS001', 'severity': 'high',
            'name': '== instead of ===',
            'description': 'Loose equality performs type coercion: 0 == "" is true, null == undefined is true.',
            'example': (
                '// BUG\n'
                'if (x == null) { ... }  // also matches undefined\n\n'
                '// FIX\n'
                'if (x === null) { ... }'
            ),
        },
        {
            'id': 'JS002', 'severity': 'high',
            'name': 'var in loop closure',
            'description': 'var is function-scoped, so loop closures all capture the same variable.',
            'example': (
                '// BUG — all print 5\n'
                'for (var i = 0; i < 5; i++) {\n'
                '    setTimeout(() => console.log(i), 100);\n'
                '}\n\n'
                '// FIX — let is block-scoped\n'
                'for (let i = 0; i < 5; i++) {\n'
                '    setTimeout(() => console.log(i), 100);\n'
                '}'
            ),
        },
        {
            'id': 'JS003', 'severity': 'high',
            'name': 'Missing await on async call',
            'description': 'Forgetting await returns a Promise object instead of the resolved value.',
            'example': (
                '// BUG\n'
                'async function getData() {\n'
                '    const res = fetch(url);  // missing await!\n'
                '    return res.json();       // calling .json() on a Promise\n'
                '}\n\n'
                '// FIX\n'
                'async function getData() {\n'
                '    const res = await fetch(url);\n'
                '    return res.json();\n'
                '}'
            ),
        },
        {
            'id': 'JS004', 'severity': 'medium',
            'name': 'this binding loss',
            'description': 'Passing a method as a callback loses `this` context.',
            'example': (
                '// BUG\n'
                'class Timer {\n'
                '    start() { setTimeout(this.tick, 1000); }  // this = undefined\n'
                '    tick() { console.log(this.count); }\n'
                '}\n\n'
                '// FIX\n'
                'start() { setTimeout(() => this.tick(), 1000); }'
            ),
        },
        {
            'id': 'JS005', 'severity': 'medium',
            'name': 'Unhandled Promise rejection',
            'description': 'A rejected promise without .catch() crashes Node.js and silently fails in browsers.',
            'example': (
                '// BUG\n'
                'fetchData().then(process);\n\n'
                '// FIX\n'
                'fetchData().then(process).catch(handleError);'
            ),
        },
        {
            'id': 'JS006', 'severity': 'low',
            'name': 'parseInt without radix',
            'description': 'parseInt("08") may be interpreted as octal in older engines.',
            'example': (
                '// BAD\n'
                'parseInt("08");\n\n'
                '// GOOD\n'
                'parseInt("08", 10);'
            ),
        },
    ],
}

# ---------------------------------------------------------------------------
# TYPESCRIPT
# ---------------------------------------------------------------------------
_TYPESCRIPT = {
    'paradigm': 'statically-typed superset of JavaScript, compiled/transpiled',

    'style_guide': {
        'name': 'TypeScript Best Practices',
        'key_rules': [
            'Prefer interface over type alias for object shapes',
            'Avoid `any` — use `unknown` if type is uncertain',
            'Use strict mode (strict: true in tsconfig)',
            'Enable noImplicitAny, strictNullChecks',
            'Use readonly for immutable properties',
            'Use union types instead of enums where appropriate',
        ],
    },

    'error_model': {
        'type': 'compile-time type errors + JavaScript runtime exceptions',
        'description': (
            'TypeScript catches type errors at compile time but compiles down to '
            'JavaScript. Runtime behavior is identical to JS — all JS pitfalls '
            '(undefined access, NaN propagation) still apply if types are bypassed '
            'with `any` or type assertions (`as`).'
        ),
    },

    'ecosystem': {
        'package_manager': 'npm / yarn / pnpm',
        'common_frameworks': 'React, Angular, NestJS, Next.js',
        'import_style': "import { x } from 'module'",
    },

    'bug_patterns': [
        {
            'id': 'TS001', 'severity': 'high',
            'name': 'Unsafe use of `any`',
            'description': '`any` disables type checking entirely — type errors pass through undetected.',
            'example': (
                '// BUG\n'
                'function process(data: any) {\n'
                '    return data.foo.bar;  // no compile error, runtime crash\n'
                '}\n\n'
                '// FIX\n'
                'function process(data: unknown) {\n'
                '    if (typeof data === "object" && data && "foo" in data) { ... }\n'
                '}'
            ),
        },
        {
            'id': 'TS002', 'severity': 'high',
            'name': 'Type assertion masking null',
            'description': '`as` assertions bypass null checks — the value can still be null at runtime.',
            'example': (
                '// BUG\n'
                'const el = document.getElementById("app") as HTMLElement;\n'
                'el.innerHTML = "hi";  // crash if #app missing\n\n'
                '// FIX\n'
                'const el = document.getElementById("app");\n'
                'if (el) { el.innerHTML = "hi"; }'
            ),
        },
        {
            'id': 'TS003', 'severity': 'medium',
            'name': 'Non-exhaustive switch on union type',
            'description': 'Missing a case in a switch over a union type silently ignores new variants.',
            'example': (
                '// BUG — what if Status gains a new value?\n'
                'type Status = "ok" | "error" | "pending";\n'
                'function handle(s: Status) {\n'
                '    switch (s) {\n'
                '        case "ok": return 1;\n'
                '        case "error": return 2;\n'
                '        // "pending" silently falls through\n'
                '    }\n'
                '}\n\n'
                '// FIX — exhaustiveness check\n'
                'default: const _: never = s; throw new Error(`Unhandled: ${s}`);'
            ),
        },
        {
            'id': 'TS004', 'severity': 'medium',
            'name': 'Optional chaining without nullish coalescing',
            'description': 'Using ?. alone returns undefined which may propagate silently.',
            'example': (
                '// RISKY\n'
                'const name = user?.profile?.name;  // could be undefined\n\n'
                '// BETTER\n'
                'const name = user?.profile?.name ?? "Anonymous";'
            ),
        },
    ],
}

# ---------------------------------------------------------------------------
# C++
# ---------------------------------------------------------------------------
_CPP = {
    'paradigm': 'compiled, systems-level, multi-paradigm (OOP + generic + functional)',

    'style_guide': {
        'name': 'C++ Core Guidelines / Google C++ Style',
        'key_rules': [
            'RAII for resource management — no raw new/delete',
            'Prefer smart pointers (unique_ptr, shared_ptr) over raw pointers',
            'Use const wherever possible',
            'Prefer range-based for loops',
            'Use nullptr instead of NULL or 0',
            'Header guards or #pragma once in every header',
        ],
    },

    'error_model': {
        'type': 'undefined behavior + exceptions + return codes',
        'description': (
            'C++ has three error channels: exceptions (try/catch/throw), return codes, '
            'and undefined behavior (UB). UB is the most dangerous — the compiler assumes '
            'UB never happens and optimizes accordingly. Buffer overflows, use-after-free, '
            'null pointer dereference, and signed integer overflow are all UB. '
            'Memory errors often manifest as crashes in unrelated code.'
        ),
    },

    'ecosystem': {
        'package_manager': 'vcpkg / Conan / CMake FetchContent',
        'common_frameworks': 'STL, Boost, Qt, gtest',
        'import_style': '#include <header> / #include "local.h"',
    },

    'bug_patterns': [
        {
            'id': 'CPP001', 'severity': 'high',
            'name': 'Buffer overflow / out-of-bounds access',
            'description': 'Accessing memory beyond array bounds is undefined behavior — can corrupt stack, crash, or be exploited.',
            'example': (
                '// BUG\n'
                'int arr[5];\n'
                'for (int i = 0; i <= 5; i++) arr[i] = i;  // writes arr[5]!\n\n'
                '// FIX\n'
                'for (int i = 0; i < 5; i++) arr[i] = i;\n'
                '// BETTER: use std::array with .at() for bounds checking'
            ),
        },
        {
            'id': 'CPP002', 'severity': 'high',
            'name': 'Memory leak — missing delete / free',
            'description': 'Allocating with new/malloc without corresponding delete/free leaks memory.',
            'example': (
                '// BUG\n'
                'int* p = new int[100];\n'
                'if (error) return;  // leaks p!\n'
                'delete[] p;\n\n'
                '// FIX: RAII\n'
                'auto p = std::make_unique<int[]>(100);\n'
                'if (error) return;  // unique_ptr cleans up automatically'
            ),
        },
        {
            'id': 'CPP003', 'severity': 'high',
            'name': 'Use-after-free / dangling pointer',
            'description': 'Accessing memory after it has been freed causes undefined behavior.',
            'example': (
                '// BUG\n'
                'int* p = new int(42);\n'
                'delete p;\n'
                'std::cout << *p;  // UB: use-after-free\n\n'
                '// FIX\n'
                'auto p = std::make_unique<int>(42);\n'
                '// p is automatically managed'
            ),
        },
        {
            'id': 'CPP004', 'severity': 'high',
            'name': 'Null pointer dereference',
            'description': 'Dereferencing a null pointer is undefined behavior.',
            'example': (
                '// BUG\n'
                'Node* find(int key) { ... return nullptr; }\n'
                'std::cout << find(42)->value;  // crash if not found!\n\n'
                '// FIX\n'
                'Node* result = find(42);\n'
                'if (result) std::cout << result->value;'
            ),
        },
        {
            'id': 'CPP005', 'severity': 'medium',
            'name': 'Iterator invalidation',
            'description': 'Modifying a container while iterating invalidates iterators — UB.',
            'example': (
                '// BUG\n'
                'for (auto it = vec.begin(); it != vec.end(); ++it)\n'
                '    if (*it < 0) vec.erase(it);  // invalidates it!\n\n'
                '// FIX\n'
                'vec.erase(std::remove_if(vec.begin(), vec.end(),\n'
                '    [](int x) { return x < 0; }), vec.end());'
            ),
        },
        {
            'id': 'CPP006', 'severity': 'medium',
            'name': 'Signed integer overflow',
            'description': 'Signed integer overflow is undefined behavior in C++. Unsigned wraps; signed does not.',
            'example': (
                '// BUG — UB if a + b overflows\n'
                'int mid = (low + high) / 2;\n\n'
                '// FIX\n'
                'int mid = low + (high - low) / 2;'
            ),
        },
    ],
}

# ---------------------------------------------------------------------------
# C
# ---------------------------------------------------------------------------
_C = {
    'paradigm': 'compiled, procedural, systems-level, manual memory management',

    'style_guide': {
        'name': 'Linux Kernel / CERT C Coding Standard',
        'key_rules': [
            'Always check return values of malloc, fopen, etc.',
            'Use sizeof(*ptr) instead of sizeof(Type) for malloc',
            'Declare variables at the top of scope (C89) or at point of use (C99+)',
            'Avoid magic numbers — use #define or enum',
            'Use static for file-local functions',
        ],
    },

    'error_model': {
        'type': 'return codes + errno + undefined behavior',
        'description': (
            'C has no exceptions. Errors are communicated via return codes '
            '(typically -1 or NULL) and errno. Failing to check return values '
            'is the #1 source of bugs. Undefined behavior (buffer overflows, '
            'null dereference, format string mismatches) can be exploited for '
            'security attacks.'
        ),
    },

    'ecosystem': {
        'package_manager': 'system package manager / vcpkg',
        'common_frameworks': 'POSIX, libc, glib',
        'import_style': '#include <header.h> / #include "local.h"',
    },

    'bug_patterns': [
        {
            'id': 'C001', 'severity': 'high',
            'name': 'Buffer overflow',
            'description': 'Writing beyond array bounds — #1 security vulnerability in C code.',
            'example': (
                '// BUG\n'
                'char buf[10];\n'
                'strcpy(buf, user_input);  // no length check!\n\n'
                '// FIX\n'
                'strncpy(buf, user_input, sizeof(buf) - 1);\n'
                'buf[sizeof(buf) - 1] = \'\\0\';'
            ),
        },
        {
            'id': 'C002', 'severity': 'high',
            'name': 'Memory leak',
            'description': 'Calling malloc/calloc without corresponding free.',
            'example': (
                '// BUG\n'
                'int *arr = malloc(n * sizeof(int));\n'
                'if (error) return -1;  // leaks arr!\n\n'
                '// FIX\n'
                'if (error) { free(arr); return -1; }'
            ),
        },
        {
            'id': 'C003', 'severity': 'high',
            'name': 'Unchecked malloc return',
            'description': 'malloc returns NULL on failure. Dereferencing NULL is UB.',
            'example': (
                '// BUG\n'
                'int *p = malloc(sizeof(int));\n'
                '*p = 42;  // crash if malloc returned NULL\n\n'
                '// FIX\n'
                'int *p = malloc(sizeof(int));\n'
                'if (!p) { perror("malloc"); exit(1); }\n'
                '*p = 42;'
            ),
        },
        {
            'id': 'C004', 'severity': 'high',
            'name': 'Format string mismatch',
            'description': 'printf/scanf format specifier not matching the argument type is UB.',
            'example': (
                '// BUG\n'
                'long x = 42;\n'
                'printf("%d", x);  // %d is for int, not long!\n\n'
                '// FIX\n'
                'printf("%ld", x);'
            ),
        },
        {
            'id': 'C005', 'severity': 'medium',
            'name': 'Use-after-free',
            'description': 'Accessing memory after free() causes undefined behavior.',
            'example': (
                '// BUG\n'
                'free(ptr);\n'
                'printf("%d", *ptr);  // UB!\n\n'
                '// FIX\n'
                'free(ptr);\n'
                'ptr = NULL;'
            ),
        },
    ],
}

# ---------------------------------------------------------------------------
# JAVA
# ---------------------------------------------------------------------------
_JAVA = {
    'paradigm': 'compiled to bytecode (JVM), statically-typed, OOP, garbage-collected',

    'style_guide': {
        'name': 'Google Java Style Guide',
        'key_rules': [
            'camelCase for methods/variables, PascalCase for classes',
            'Braces required even for single-line if/for/while',
            'One top-level class per file, filename must match class name',
            'Use @Override annotation on every overriding method',
            'Prefer enhanced for-loop over indexed loop',
            'Use final for variables that won\'t be reassigned',
        ],
    },

    'error_model': {
        'type': 'checked + unchecked exceptions',
        'description': (
            'Java has two categories: checked exceptions (must be caught or declared) '
            'and unchecked exceptions (RuntimeException subclasses). '
            'NullPointerException is the most common bug. '
            'Resources should be managed with try-with-resources (AutoCloseable). '
            'Catching generic Exception or Throwable is usually a code smell.'
        ),
    },

    'ecosystem': {
        'package_manager': 'Maven / Gradle',
        'common_frameworks': 'Spring Boot, JUnit, Hibernate, Jakarta EE',
        'import_style': 'import com.example.ClassName',
    },

    'bug_patterns': [
        {
            'id': 'JAVA001', 'severity': 'high',
            'name': 'NullPointerException risk',
            'description': 'Calling methods on a potentially null reference without checking.',
            'example': (
                '// BUG\n'
                'String name = map.get("key");\n'
                'int len = name.length();  // NPE if key missing!\n\n'
                '// FIX\n'
                'String name = map.getOrDefault("key", "");\n'
                '// OR\n'
                'Optional<String> name = Optional.ofNullable(map.get("key"));'
            ),
        },
        {
            'id': 'JAVA002', 'severity': 'high',
            'name': 'Resource leak — unclosed stream/connection',
            'description': 'Opening a resource without try-with-resources or finally block leaks handles.',
            'example': (
                '// BUG\n'
                'FileReader fr = new FileReader("f.txt");\n'
                'fr.read();  // if this throws, fr is never closed\n\n'
                '// FIX\n'
                'try (FileReader fr = new FileReader("f.txt")) {\n'
                '    fr.read();\n'
                '}'
            ),
        },
        {
            'id': 'JAVA003', 'severity': 'high',
            'name': 'String comparison with ==',
            'description': '== compares references, not content. Use .equals() for string value comparison.',
            'example': (
                '// BUG\n'
                'if (input == "admin") { ... }  // compares references!\n\n'
                '// FIX\n'
                'if ("admin".equals(input)) { ... }  // null-safe too'
            ),
        },
        {
            'id': 'JAVA004', 'severity': 'medium',
            'name': 'ConcurrentModificationException',
            'description': 'Modifying a collection while iterating with for-each throws at runtime.',
            'example': (
                '// BUG\n'
                'for (String s : list)\n'
                '    if (s.isEmpty()) list.remove(s);  // CME!\n\n'
                '// FIX\n'
                'list.removeIf(String::isEmpty);'
            ),
        },
        {
            'id': 'JAVA005', 'severity': 'medium',
            'name': 'Catching generic Exception',
            'description': 'Catching Exception or Throwable hides the specific error type and masks bugs.',
            'example': (
                '// BAD\n'
                'try { ... } catch (Exception e) { log(e); }\n\n'
                '// GOOD\n'
                'try { ... } catch (IOException | ParseException e) { log(e); }'
            ),
        },
    ],
}

# ---------------------------------------------------------------------------
# GENERIC FALLBACK
# ---------------------------------------------------------------------------
_GENERIC = {
    'paradigm': 'unknown',

    'style_guide': {
        'name': 'General best practices',
        'key_rules': [
            'Consistent indentation',
            'Meaningful variable and function names',
            'No magic numbers — use named constants',
            'Keep functions short and focused',
        ],
    },

    'error_model': {
        'type': 'unknown',
        'description': 'Unable to determine the error handling model for this language. Apply general best practices.',
    },

    'ecosystem': {
        'package_manager': 'unknown',
        'common_frameworks': 'unknown',
        'import_style': 'unknown',
    },

    'bug_patterns': [],
}

# ---------------------------------------------------------------------------
# PROFILE REGISTRY
# ---------------------------------------------------------------------------
PROFILES = {
    'python':     _PYTHON,
    'javascript': _JAVASCRIPT,
    'typescript':  _TYPESCRIPT,
    'cpp':        _CPP,
    'c':          _C,
    'java':       _JAVA,
    '_generic':   _GENERIC,
    # Aliases — these languages share a profile or use generic
    'html':       _GENERIC,
    'css':        _GENERIC,
    'json':       _GENERIC,
    'yaml':       _GENERIC,
    'toml':       _GENERIC,
    'markdown':   _GENERIC,
    'plaintext':  _GENERIC,
    'bash':       _GENERIC,
    'rust':       _GENERIC,
    'go':         _GENERIC,
}
