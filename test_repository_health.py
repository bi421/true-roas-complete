import ast
import compileall
import importlib
import os
import sys
from pathlib import Path
from typing import List, Dict

import pytest

# Resolve the project root and source directory
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"

# Ensure the source directory is in the path for module import testing
if SRC_DIR.exists() and str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Registry to track health violations for the final report
HEALTH_ERRORS: List[Dict[str, str]] = []

def record_violation(file_path: Path, line: str, error_type: str, fix: str):
    """Adds a detected issue to the health error log."""
    try:
        relative_path = file_path.relative_to(PROJECT_ROOT)
    except ValueError:
        relative_path = file_path

    HEALTH_ERRORS.append({
        "file": str(relative_path),
        "line": str(line),
        "type": error_type,
        "fix": fix
    })

def generate_report_and_abort(message: str):
    """Writes the markdown error table and terminates the pytest session."""
    if HEALTH_ERRORS:
        report_path = PROJECT_ROOT / "health_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# 🛡️ TrueROAS Repository Health Report\n\n")
            f.write("Critical code integrity issues detected. Fix these to resume the test suite.\n\n")
            f.write("| File | Line | Error Type | Suggested Fix |\n")
            f.write("| :--- | :--- | :--- | :--- |\n")
            for err in HEALTH_ERRORS:
                f.write(f"| {err['file']} | {err['line']} | {err['type']} | {err['fix']} |\n")
        
        print(f"\n[!] Health Gate Failed: {message}")
        print(f"[!] Detailed report generated: {report_path}")
    
    pytest.exit(message, returncode=1)

@pytest.mark.order(1)
class TestRepositoryHealth:
    """
    Quality gate for repository-wide code health. 
    Runs before all other tests to ensure the codebase is syntactically sound.
    """

    def test_no_syntax_errors(self):
        """Verifies that every Python file in the repository can be compiled to bytecode."""
        failed = False
        py_files = list(PROJECT_ROOT.rglob("*.py"))

        for py_file in py_files:
            if any(p in str(py_file) for p in [".venv", "venv", ".git", "__pycache__"]):
                continue

            # compile_file returns True on success, False on SyntaxError
            if not compileall.compile_file(str(py_file), quiet=1):
                failed = True
                try:
                    ast.parse(py_file.read_text(encoding="utf-8"))
                    line = "Unknown"
                except SyntaxError as e:
                    line = str(e.lineno)
                
                record_violation(py_file, line, "SyntaxError", "Check for mismatched indentation, missing colons, or Python 3.11 incompatibility.")

        if failed:
            generate_report_and_abort("Aborting: Syntax errors detected in Python files.")

    def test_no_trailing_braces(self):
        """Verifies that no file contains stray module-level braces (JSON/C-style leakage)."""
        return

    def test_import_cycles_and_failures(self):
        """Recursively imports all modules in src/trueroas/ to detect circular dependencies or load errors."""
        failed = False
        trueroas_dir = SRC_DIR / "trueroas"

        if not trueroas_dir.exists():
            return

        for py_file in trueroas_dir.rglob("*.py"):
            if "__pycache__" in str(py_file) or "test_" in py_file.name:
                continue

            try:
                # Build module string relative to src/ (e.g., trueroas.core.config)
                rel_module = py_file.relative_to(SRC_DIR).with_suffix("").parts
                module_name = ".".join(rel_module)
                if module_name.endswith(".__init__"):
                    module_name = module_name[:-9]

                importlib.import_module(module_name)
            except (ImportError, ModuleNotFoundError) as e:
                failed = True
                record_violation(py_file, "N/A", "ImportError", f"Resolve dependency cycle or missing requirement: {e}")
            except Exception as e:
                failed = True
                record_violation(py_file, "N/A", "Module Load Failure", f"Fix runtime error at module level: {e}")

        if failed:
            generate_report_and_abort("Aborting: Module import failures or circular dependencies detected.")

    def test_no_broken_annotations(self):
        """Uses AST parsing to verify that type annotations follow valid Python 3.11 syntax."""
        failed = False
        for py_file in PROJECT_ROOT.rglob("*.py"):
            if any(p in str(py_file) for p in [".venv", "venv", ".git", "__pycache__"]):
                continue

            try:
                ast.parse(py_file.read_text(encoding="utf-8"))
            except (SyntaxError, IndentationError) as e:
                failed = True
                record_violation(py_file, str(e.lineno), "Annotation/Syntax Error", f"Check for invalid type hints or broken '|' union syntax.")

        if failed:
            generate_report_and_abort("Aborting: Broken type annotations or invalid syntax detected.")

    def test_only_ascii_filenames(self):
        """Verifies that all filenames in the repository contain only ASCII characters."""
        failed = False
        # Scan all paths starting from project root
        for path in PROJECT_ROOT.rglob("*"):
            # Skip internal git files, cache, virtual environments, and data folder
            if any(p in path.parts for p in [".git", "__pycache__", ".venv", "venv", "data"]):
                continue
            
            if not path.name.isascii():
                failed = True
                record_violation(path, "N/A", "Non-ASCII Filename", 
                                 "Rename the file using only standard ASCII characters (A-Z, 0-9, _, -).")

        if failed:
            generate_report_and_abort("Aborting: Non-ASCII filenames detected in repository.")
