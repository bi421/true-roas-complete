import ast
import os
import sys

def check_syntax():
    """Walks all .py files and attempts ast.parse() to detect syntax or indentation errors."""
    errors_found = False
    # Target root and common directories
    targets = ['src', 'scripts', '.']
    
    for target in targets:
        if not os.path.exists(target):
            continue
            
        for root, _, files in os.walk(target):
            # Skip hidden directories and virtual environments
            if any(part.startswith('.') for part in root.split(os.sep)) or 'venv' in root:
                continue
                
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            source = f.read()
                        ast.parse(source, filename=file_path)
                    except (SyntaxError, IndentationError) as e:
                        print(f"CRITICAL SYNTAX FAILURE: {file_path}")
                        print(f"  Line {e.lineno}, Col {e.offset}: {e.msg}")
                        if e.text:
                            print(f"  Code Context: {e.text.strip()}")
                        errors_found = True
                        
    return errors_found

if __name__ == "__main__":
    if check_syntax():
        print("\nResult: Pipeline Blocked. Syntax errors must be resolved.")
        sys.exit(1)
    print("\nResult: All files parsed successfully.")
    sys.exit(0)