#  Copyright (c) 2024-2026 TrueROAS Team.
#  All rights reserved.
#  Proprietary and confidential.

import ast
import os
import sys
from typing import Any

EXCLUDED_NUMBERS = {0, 1, -1, 2}
MATH_CONSTANTS = {"pi", "e", "tau"}


class MagicNumberVisitor(ast.NodeVisitor):
    def __init__(self, filename: str, source: str):
        self.filename = filename
        self.source_lines = source.splitlines()
        self.findings = []
        self.in_function = False

    def visit_FunctionDef(self, node):
        self.in_function = True
        self.generic_visit(node)
        self.in_function = False

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)

    def visit_Constant(self, node):
        if not self.in_function:
            return
        if not isinstance(node.value, (int, float)):
            return
        if node.value in EXCLUDED_NUMBERS:
            return

        parent = getattr(node, "parent", None)

        # Rule: Exclude array indices
        if isinstance(parent, ast.Subscript):
            return

        # Rule: Exclude assignments to UPPER_SNAKE_CASE
        if isinstance(parent, ast.Assign):
            for target in parent.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    return

        # Rule: Exclude math constants (math.pi etc)
        if isinstance(parent, ast.Attribute):
            if isinstance(parent.value, ast.Name) and parent.value.id == "math":
                if parent.attr in MATH_CONSTANTS:
                    return
            # Rule: Exclude settings/config access
            if isinstance(parent.value, ast.Name) and parent.value.id in {
                "settings",
                "config",
            }:
                return

        # Severity Classification
        severity = "MEDIUM"
        context = "Arithmetic/Constant"

        if isinstance(parent, ast.Compare):
            severity = "CRITICAL"
            context = "Threshold Comparison"
        elif isinstance(parent, ast.BinOp):
            severity = "HIGH"
            context = "Arithmetic Formula"
        elif (
            isinstance(parent, ast.Call)
            and isinstance(parent.func, ast.Name)
            and parent.func.id == "round"
        ):
            severity = "MEDIUM"
            context = "Rounding"

        # Auto-refactor suggestion logic
        suggested = self._suggest_constant_name(node, parent)

        self.findings.append(
            {
                "file": self.filename,
                "line": node.lineno,
                "number": node.value,
                "context": context,
                "suggested": suggested,
                "severity": severity,
            }
        )

    def _suggest_constant_name(self, node: ast.Constant, parent: Any) -> str:
        """Guesses a useful constant name based on context."""
        prefix = "BAYESIAN" if "inference" in self.filename else "STRATEGIC"

        # Try to find a nearby variable name
        context_name = "VAL"
        if isinstance(parent, ast.Assign):
            if isinstance(parent.targets[0], ast.Name):
                context_name = parent.targets[0].id.upper()
        elif isinstance(parent, ast.Compare):
            if isinstance(parent.left, ast.Name):
                context_name = f"{parent.left.id.upper()}_THRESHOLD"

        return f"settings.{prefix}_{context_name}"


def audit_files(root_dir: str):
    all_findings = []

    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".py") and not file.startswith("test_"):
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8") as f:
                    source = f.read()

                tree = ast.parse(source)

                # Manually link parents
                for parent in ast.walk(tree):
                    for child in ast.iter_child_nodes(parent):
                        child.parent = parent

                visitor = MagicNumberVisitor(path, source)
                visitor.visit(tree)
                all_findings.extend(visitor.findings)

    return all_findings


if __name__ == "__main__":
    src_path = os.path.join(os.getcwd(), "src")
    findings = audit_files(src_path)

    if not findings:
        print("✅ No magic numbers detected.")
        sys.exit(0)

    # Output Markdown Table
    print("# 🕵️ Magic Number Audit Report\n")
    print("| File | Line | Number | Context | Suggested Constant | Severity |")
    print("| :--- | :--- | :--- | :--- | :--- | :--- |")

    critical_count = 0
    for f in findings:
        rel_path = os.path.relpath(f["file"], os.getcwd())
        print(
            f"| {rel_path} | {f['line']} | `{f['number']}` | {f['context']} | `{f['suggested']}` | {f['severity']} |"
        )
        if f["severity"] == "CRITICAL":
            critical_count += 1

    if critical_count > 0:
        print(
            f"\n❌ FAILED: {critical_count} CRITICAL threshold magic numbers found. CI Gate Blocked."
        )
        sys.exit(1)
    else:
        print("\n⚠️ WARNING: Magic numbers found. Please refactor to settings.py.")
        sys.exit(0)
