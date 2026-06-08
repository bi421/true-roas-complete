from pathlib import Path

# Copyright header configuration
COPYRIGHT_TEXT = "Copyright (c) 2024-2026 TrueROAS Team"

HEADERS = {
    ".py": f"#  {COPYRIGHT_TEXT}.\n#  All rights reserved.\n#  Proprietary and confidential.\n\n",
    ".yml": f"#  {COPYRIGHT_TEXT}.\n#  All rights reserved.\n#  Proprietary and confidential.\n\n",
    ".yaml": f"#  {COPYRIGHT_TEXT}.\n#  All rights reserved.\n#  Proprietary and confidential.\n\n",
    ".html": f"<!--\n  {COPYRIGHT_TEXT}.\n  All rights reserved.\n  Proprietary and confidential.\n-->\n\n",
    ".css": f"/*\n  {COPYRIGHT_TEXT}.\n  All rights reserved.\n  Proprietary and confidential.\n*/\n\n",
}

IGNORE_DIRS = {".git", "__pycache__", "venv", "node_modules", "data"}


def apply_copyright(root_dir: Path) -> None:
    """
    Recursively applies the copyright header to all supported source files.
    """
    applied_count = 0
    skipped_count = 0

    for path in root_dir.rglob("*"):
        # Skip directories and ignored paths
        if path.is_dir() or any(part in IGNORE_DIRS for part in path.parts):
            continue

        # Check if file extension is supported
        if path.suffix not in HEADERS:
            continue

        header = HEADERS[path.suffix]

        try:
            content = path.read_text(encoding="utf-8")

            # Check if header already exists
            if COPYRIGHT_TEXT in content:
                print(f"[-] Already exists, skipping: {path.relative_to(root_dir)}")
                skipped_count += 1
                continue

            # Special handling for Python shebangs (#!/usr/bin/env python)
            new_content = ""
            if content.startswith("#!"):
                lines = content.splitlines(keepends=True)
                shebang = lines[0]
                rest = "".join(lines[1:])
                new_content = shebang + "\n" + header + rest
            else:
                new_content = header + content

            path.write_text(new_content, encoding="utf-8")
            print(f"[+] Applied header to: {path.relative_to(root_dir)}")
            applied_count += 1

        except Exception as e:
            print(f"[!] Error processing {path}: {e}")

    print("\n--- Process Complete ---")
    print(f"Headers applied: {applied_count}")
    print(f"Files skipped: {skipped_count}")


if __name__ == "__main__":
    # Locate the project root (assuming the script is in /scripts directory)
    current_dir = Path(__file__).parent
    project_root = current_dir.parent

    print(f"Starting copyright application in: {project_root}\n")
    apply_copyright(project_root)
