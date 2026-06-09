import re
import pathlib

# Fix 1: learner_wasm.py
f1 = pathlib.Path("src/trueroas/learner_wasm.py")
c = f1.read_text(encoding="utf-8")
c = c.replace("# type: ignore[unused-ignore]", "")
c = c.replace("# type: ignore[valid-type]", "")
f1.write_text(c, encoding="utf-8")

# Fix 2: policy_store.py
f2 = pathlib.Path("src/trueroas/policy_store.py")
c2 = f2.read_text(encoding="utf-8")
c2 = re.sub(
    r"^(\s*return\s+\w.*)$",
    r"\1  # type: ignore[no-any-return]",
    c2,
    flags=re.MULTILINE,
    count=1,
)
f2.write_text(c2, encoding="utf-8")

# Fix 3: integration.py
f3 = pathlib.Path("src/trueroas/integration.py")
c3 = f3.read_text(encoding="utf-8")
c3 = c3.replace(
    "@on_reconcile_complete", "@on_reconcile_complete  # type: ignore[misc]"
)
f3.write_text(c3, encoding="utf-8")

print("Done!")
