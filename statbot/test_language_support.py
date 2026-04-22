"""
Unit tests for the language_support module.

Run: python -m pytest test_language_support.py -v
"""

import os
import tempfile
import pytest

from language_support.detection import detect_language, LanguageInfo
from language_support.profiles import get_profile, PROFILES
from language_support.prompt_builder import build_analysis_prompt
from language_support.registry import EXTENSION_MAP


# ===================================================================
# DETECTION TESTS
# ===================================================================

class TestExtensionDetection:
    """Tier 1: Extension-based detection."""

    def test_python_py(self):
        assert detect_language("app.py").key == "python"

    def test_python_pyi(self):
        assert detect_language("stubs.pyi").key == "python"

    def test_javascript_js(self):
        assert detect_language("index.js").key == "javascript"

    def test_javascript_jsx(self):
        assert detect_language("Component.jsx").key == "javascript"

    def test_javascript_mjs(self):
        assert detect_language("module.mjs").key == "javascript"

    def test_typescript_ts(self):
        assert detect_language("app.ts").key == "typescript"

    def test_typescript_tsx(self):
        assert detect_language("Component.tsx").key == "typescript"

    def test_cpp_cpp(self):
        assert detect_language("main.cpp").key == "cpp"

    def test_cpp_cc(self):
        assert detect_language("main.cc").key == "cpp"

    def test_cpp_hpp(self):
        assert detect_language("header.hpp").key == "cpp"

    def test_c_extension(self):
        assert detect_language("utils.c").key == "c"

    def test_java_extension(self):
        assert detect_language("Main.java").key == "java"

    def test_html_extension(self):
        assert detect_language("index.html").key == "html"

    def test_css_extension(self):
        assert detect_language("style.css").key == "css"

    def test_json_extension(self):
        assert detect_language("package.json").key == "json"


class TestCaseInsensitivity:
    """Extension detection should be case-insensitive."""

    def test_uppercase_py(self):
        assert detect_language("App.PY").key == "python"

    def test_mixed_case_js(self):
        assert detect_language("Bundle.Js").key == "javascript"

    def test_uppercase_cpp(self):
        assert detect_language("main.CPP").key == "cpp"

    def test_uppercase_java(self):
        assert detect_language("Main.JAVA").key == "java"


class TestDoubleExtensions:
    """Should strip .test. / .spec. / .min. prefixes."""

    def test_test_js(self):
        assert detect_language("utils.test.js").key == "javascript"

    def test_spec_ts(self):
        assert detect_language("component.spec.ts").key == "typescript"

    def test_min_js(self):
        assert detect_language("bundle.min.js").key == "javascript"

    def test_d_ts(self):
        assert detect_language("types.d.ts").key == "typescript"


class TestAmbiguousH:
    """Tier 1 special case: .h files need content disambiguation."""

    def test_h_with_cpp_content(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.h', delete=False, encoding='utf-8') as f:
            f.write('#include <iostream>\nnamespace foo {\nclass Bar {};\n}\n')
            f.flush()
            result = detect_language(f.name)
        os.unlink(f.name)
        assert result.key == "cpp"

    def test_h_with_c_content(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.h', delete=False, encoding='utf-8') as f:
            f.write('#include <stdio.h>\nvoid foo(int x);\n')
            f.flush()
            result = detect_language(f.name)
        os.unlink(f.name)
        assert result.key == "c"


class TestFilenameDetection:
    """Tier 2: Known filename detection."""

    def test_makefile(self):
        with tempfile.NamedTemporaryFile(mode='w', prefix='Makefile', suffix='', delete=False, dir='.') as f:
            f.write('all:\n\techo hello\n')
            fname = f.name
        # Need a file named exactly "Makefile"
        makefile_path = os.path.join('.', 'Makefile_test_detection')
        os.rename(fname, makefile_path)
        # This won't match since filename is Makefile_test_detection, not Makefile
        # So test with a properly named file instead
        os.unlink(makefile_path)

        # Direct test - the detector checks basename
        # Create a real Makefile in a temp dir
        with tempfile.TemporaryDirectory() as tmpdir:
            mpath = os.path.join(tmpdir, 'Makefile')
            with open(mpath, 'w') as f:
                f.write('all:\n\techo hello\n')
            result = detect_language(mpath)
            assert result.key == "makefile"

    def test_dockerfile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            dpath = os.path.join(tmpdir, 'Dockerfile')
            with open(dpath, 'w') as f:
                f.write('FROM python:3.11\n')
            result = detect_language(dpath)
            assert result.key == "dockerfile"


class TestShebangDetection:
    """Tier 3: Shebang-based detection."""

    def test_python_shebang(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='', delete=False, encoding='utf-8') as f:
            f.write('#!/usr/bin/env python3\nprint("hello")\n')
            f.flush()
            result = detect_language(f.name)
        os.unlink(f.name)
        assert result.key == "python"

    def test_node_shebang(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='', delete=False, encoding='utf-8') as f:
            f.write('#!/usr/bin/env node\nconsole.log("hi")\n')
            f.flush()
            result = detect_language(f.name)
        os.unlink(f.name)
        assert result.key == "javascript"

    def test_bash_shebang(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='', delete=False, encoding='utf-8') as f:
            f.write('#!/bin/bash\necho hello\n')
            f.flush()
            result = detect_language(f.name)
        os.unlink(f.name)
        assert result.key == "bash"


class TestContentHeuristics:
    """Tier 4: Content-based detection."""

    def test_java_content(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='', delete=False, encoding='utf-8') as f:
            f.write('public class Main {\n    public static void main(String[] args) {}\n}\n')
            f.flush()
            result = detect_language(f.name)
        os.unlink(f.name)
        assert result.key == "java"

    def test_go_content(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='', delete=False, encoding='utf-8') as f:
            f.write('package main\n\nimport "fmt"\n\nfunc main() {\n    fmt.Println("hi")\n}\n')
            f.flush()
            result = detect_language(f.name)
        os.unlink(f.name)
        assert result.key == "go"

    def test_html_content(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='', delete=False, encoding='utf-8') as f:
            f.write('<!DOCTYPE html>\n<html><body>hi</body></html>\n')
            f.flush()
            result = detect_language(f.name)
        os.unlink(f.name)
        assert result.key == "html"


class TestGenericFallback:
    """Tier 5: Unknown files should fall back to _generic."""

    def test_unknown_extension(self):
        assert detect_language("mystery.xyz").key == "_generic"

    def test_no_extension_no_content(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='', delete=False, encoding='utf-8') as f:
            f.write('just some random text\n')
            f.flush()
            result = detect_language(f.name)
        os.unlink(f.name)
        assert result.key == "_generic"

    def test_empty_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.xyz', delete=False, encoding='utf-8') as f:
            f.write('')
            f.flush()
            result = detect_language(f.name)
        os.unlink(f.name)
        assert result.key == "_generic"


class TestEdgeCases:
    """Edge cases that shouldn't crash."""

    def test_filename_with_spaces(self):
        result = detect_language("my file.py")
        assert result.key == "python"

    def test_path_with_directory(self):
        result = detect_language("src/components/Button.tsx")
        assert result.key == "typescript"

    def test_deeply_nested_path(self):
        result = detect_language("a/b/c/d/e/main.cpp")
        assert result.key == "cpp"


class TestLanguageInfoStructure:
    """Verify LanguageInfo namedtuple has correct fields."""

    def test_has_key(self):
        info = detect_language("test.py")
        assert hasattr(info, 'key')

    def test_has_name(self):
        info = detect_language("test.py")
        assert info.name == "Python"

    def test_has_fence(self):
        info = detect_language("test.py")
        assert info.fence == "python"

    def test_js_display(self):
        info = detect_language("test.js")
        assert info.name == "JavaScript"
        assert info.fence == "javascript"

    def test_cpp_display(self):
        info = detect_language("test.cpp")
        assert info.name == "C++"
        assert info.fence == "cpp"


# ===================================================================
# PROFILE TESTS
# ===================================================================

class TestProfileLoading:
    """Verify profiles load correctly for all supported languages."""

    def test_python_profile(self):
        p = get_profile('python')
        assert p['style_guide']['name'] == 'PEP 8'
        assert len(p['bug_patterns']) > 0
        pattern_ids = [bp['id'] for bp in p['bug_patterns']]
        assert 'PY001' in pattern_ids

    def test_javascript_profile(self):
        p = get_profile('javascript')
        assert 'Airbnb' in p['style_guide']['name']
        assert 'undefined' in p['error_model']['type']
        pattern_ids = [bp['id'] for bp in p['bug_patterns']]
        assert 'JS001' in pattern_ids

    def test_typescript_profile(self):
        p = get_profile('typescript')
        assert 'any' in p['bug_patterns'][0]['name'].lower()
        pattern_ids = [bp['id'] for bp in p['bug_patterns']]
        assert 'TS001' in pattern_ids

    def test_cpp_profile(self):
        p = get_profile('cpp')
        assert 'memory' in p['error_model']['description'].lower() or 'undefined' in p['error_model']['description'].lower()
        pattern_ids = [bp['id'] for bp in p['bug_patterns']]
        assert 'CPP001' in pattern_ids

    def test_c_profile(self):
        p = get_profile('c')
        assert 'return code' in p['error_model']['type'].lower() or 'return codes' in p['error_model']['type'].lower()
        pattern_ids = [bp['id'] for bp in p['bug_patterns']]
        assert 'C001' in pattern_ids

    def test_java_profile(self):
        p = get_profile('java')
        assert 'checked' in p['error_model']['type'].lower()
        pattern_ids = [bp['id'] for bp in p['bug_patterns']]
        assert 'JAVA001' in pattern_ids

    def test_generic_profile(self):
        p = get_profile('_generic')
        assert len(p['bug_patterns']) == 0

    def test_unknown_key_falls_back_to_generic(self):
        p = get_profile('nonexistent_language')
        assert p == PROFILES['_generic']

    def test_all_profiles_have_required_keys(self):
        required = {'paradigm', 'style_guide', 'error_model', 'bug_patterns'}
        for key, profile in PROFILES.items():
            for req in required:
                assert req in profile, f"Profile '{key}' missing key '{req}'"

    def test_all_patterns_have_required_fields(self):
        required = {'id', 'severity', 'name', 'description', 'example'}
        for key, profile in PROFILES.items():
            for pattern in profile['bug_patterns']:
                for req in required:
                    assert req in pattern, f"Pattern '{pattern.get('id', '?')}' in '{key}' missing '{req}'"


# ===================================================================
# PROMPT BUILDER TESTS
# ===================================================================

class TestPromptBuilder:
    """Verify prompts are correctly constructed per language."""

    def test_python_prompt_contains_pep8(self):
        lang = LanguageInfo(key='python', name='Python', fence='python')
        prompt = build_analysis_prompt("test.py", "print('hi')", lang)
        assert "PEP 8" in prompt

    def test_python_prompt_contains_python_fence(self):
        lang = LanguageInfo(key='python', name='Python', fence='python')
        prompt = build_analysis_prompt("test.py", "print('hi')", lang)
        assert "```python" in prompt

    def test_python_prompt_contains_pattern(self):
        lang = LanguageInfo(key='python', name='Python', fence='python')
        prompt = build_analysis_prompt("test.py", "print('hi')", lang)
        assert "PY001" in prompt
        assert "Mutable default" in prompt

    def test_js_prompt_contains_airbnb(self):
        lang = LanguageInfo(key='javascript', name='JavaScript', fence='javascript')
        prompt = build_analysis_prompt("test.js", "console.log('hi')", lang)
        assert "Airbnb" in prompt

    def test_js_prompt_contains_js_fence(self):
        lang = LanguageInfo(key='javascript', name='JavaScript', fence='javascript')
        prompt = build_analysis_prompt("test.js", "console.log('hi')", lang)
        assert "```javascript" in prompt

    def test_js_prompt_contains_equality_pattern(self):
        lang = LanguageInfo(key='javascript', name='JavaScript', fence='javascript')
        prompt = build_analysis_prompt("test.js", "console.log('hi')", lang)
        assert "===" in prompt

    def test_cpp_prompt_contains_memory_concerns(self):
        lang = LanguageInfo(key='cpp', name='C++', fence='cpp')
        prompt = build_analysis_prompt("test.cpp", "int main(){}", lang)
        assert "```cpp" in prompt
        assert "CPP001" in prompt

    def test_generic_prompt_has_no_patterns(self):
        lang = LanguageInfo(key='_generic', name='Unknown', fence='text')
        prompt = build_analysis_prompt("mystery", "some content", lang)
        assert "BUG PATTERN CHECKLIST" not in prompt
        assert "```text" in prompt

    def test_custom_request_augments_not_replaces(self):
        lang = LanguageInfo(key='python', name='Python', fence='python')
        prompt = build_analysis_prompt("test.py", "x=1", lang, custom_request="What does this do?")
        # Custom request should be present
        assert "What does this do?" in prompt
        # Language-specific checks should ALSO be present
        assert "PEP 8" in prompt
        assert "PY001" in prompt
        # Should say "Additionally"
        assert "Additionally" in prompt

    def test_custom_request_none_uses_default(self):
        lang = LanguageInfo(key='python', name='Python', fence='python')
        prompt = build_analysis_prompt("test.py", "x=1", lang, custom_request=None)
        assert "ANALYSIS INSTRUCTIONS" in prompt
        assert "USER REQUEST" not in prompt

    def test_prompt_contains_output_format(self):
        lang = LanguageInfo(key='python', name='Python', fence='python')
        prompt = build_analysis_prompt("test.py", "x=1", lang)
        assert "OUTPUT FORMAT" in prompt
        assert "Bug Report" in prompt
        assert "Verdict" in prompt

    def test_prompt_contains_error_model(self):
        lang = LanguageInfo(key='java', name='Java', fence='java')
        prompt = build_analysis_prompt("Test.java", "class T{}", lang)
        assert "ERROR HANDLING MODEL" in prompt
        assert "checked" in prompt.lower()

    def test_prompt_contains_file_content(self):
        code = "def hello(): return 42"
        lang = LanguageInfo(key='python', name='Python', fence='python')
        prompt = build_analysis_prompt("test.py", code, lang)
        assert code in prompt

    def test_patterns_sorted_by_severity(self):
        lang = LanguageInfo(key='python', name='Python', fence='python')
        prompt = build_analysis_prompt("test.py", "x=1", lang)
        # HIGH patterns should appear before MEDIUM patterns
        high_pos = prompt.find("[HIGH]")
        medium_pos = prompt.find("[MEDIUM]")
        if high_pos != -1 and medium_pos != -1:
            assert high_pos < medium_pos


# ===================================================================
# INTEGRATION TESTS (end-to-end detection → prompt)
# ===================================================================

class TestEndToEnd:
    """Test the full pipeline: file → detect → prompt."""

    def test_python_file_e2e(self):
        lang = detect_language("demo_code.py")
        assert lang.key == "python"
        prompt = build_analysis_prompt("demo_code.py", "x = 1", lang)
        assert "Python" in prompt
        assert "PEP 8" in prompt

    def test_js_file_e2e(self):
        lang = detect_language("demo_code.js")
        assert lang.key == "javascript"
        prompt = build_analysis_prompt("demo_code.js", "var x = 1;", lang)
        assert "JavaScript" in prompt
        assert "Airbnb" in prompt

    def test_cpp_file_e2e(self):
        lang = detect_language("demo_code.cpp")
        assert lang.key == "cpp"
        prompt = build_analysis_prompt("demo_code.cpp", "int main(){}", lang)
        assert "C++" in prompt
        assert "memory" in prompt.lower() or "buffer" in prompt.lower()

    def test_ts_file_e2e(self):
        lang = detect_language("app.ts")
        assert lang.key == "typescript"
        prompt = build_analysis_prompt("app.ts", "const x: number = 1;", lang)
        assert "TypeScript" in prompt

    def test_java_file_e2e(self):
        lang = detect_language("Main.java")
        assert lang.key == "java"
        prompt = build_analysis_prompt("Main.java", "public class Main {}", lang)
        assert "Java" in prompt
        assert "NullPointerException" in prompt or "JAVA001" in prompt
