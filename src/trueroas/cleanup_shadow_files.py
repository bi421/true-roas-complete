import os
from pathlib import Path


def cleanup_shadow_files(root_dir: Path) -> None:
    """
    Identifies and deletes shadow files from the root directory and src/trueroas/
    that duplicate canonical files in src/trueroas/learning/.
    """
    print(f"Starting shadow file cleanup in {root_dir}")

    # Define canonical locations for learning modules
    canonical_learning_path = root_dir / "src" / "trueroas" / "learning"
    canonical_trueroas_path = root_dir / "src" / "trueroas"

    # Files that should only exist in src/trueroas/learning/
    learning_module_names = [
        "auto_tuner.py",
        "bootstrap.py",
        "config.py",
        "integration.py",
        "migrate.py",
        "policy_store.py",
        "regime_detector.py",
        "worm_proof.py",
        "__init__.py",  # Only delete if it's a duplicate of learning/__init__.py
    ]

    # Files that should only exist in src/trueroas/ (e.g., Cargo.toml, lib.rs)
    trueroas_root_module_names = [
        "__init__.py",  # Only delete if it's a duplicate of src/trueroas/__init__.py
        "Cargo.toml",
        "lib.rs",
    ]

    # Temporary fix scripts to delete
    temp_fix_scripts = [
        "fix_bootstrap.py",
        "fix_last3.py",
    ]

    files_to_delete = []

    # 1. Check root directory for shadow files
    for module_name in learning_module_names + trueroas_root_module_names:
        root_file = root_dir / module_name
        if root_file.is_file():
            # Check if a canonical version exists in learning or src/trueroas
            if (canonical_learning_path / module_name).is_file() or (
                canonical_trueroas_path / module_name
            ).is_file():
                files_to_delete.append(root_file)

    # 2. Check src/trueroas/ for shadow files of learning modules
    for module_name in learning_module_names:
        src_trueroas_file = canonical_trueroas_path / module_name
        if (
            src_trueroas_file.is_file()
            and (canonical_learning_path / module_name).is_file()
        ):
            files_to_delete.append(src_trueroas_file)

    # 3. Add temporary fix scripts to delete list
    for script_name in temp_fix_scripts:
        script_path = root_dir / script_name
        if script_path.is_file():
            files_to_delete.append(script_path)

    if not files_to_delete:
        print("No shadow files or temporary fix scripts found for deletion.")
        return

    print("\nIdentified files for deletion:")
    for f in files_to_delete:
        print(f"- {f.relative_to(root_dir)}")

    confirm = input("\nConfirm deletion of these files? (yes/no): ").lower()
    if confirm == "yes":
        for f in files_to_delete:
            try:
                os.remove(f)
                print(f"Deleted: {f.relative_to(root_dir)}")
            except OSError as e:
                print(f"Error deleting {f.relative_to(root_dir)}: {e}")
        print("\nShadow file cleanup complete.")
    else:
        print("Deletion cancelled.")


if __name__ == "__main__":
    # Correctly identify project root (two levels up from src/trueroas/)
    project_root = Path(__file__).resolve().parent.parent.parent
    cleanup_shadow_files(project_root)
