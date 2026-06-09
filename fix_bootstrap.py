content = open("bootstrap.py", "r").read()
content = content.replace(
    "                if not row or not row[0]:\n    return 1.54",
    "                if not row or not row[0]:\n                    return 1.54",
)
open("bootstrap.py", "w").write(content)
print("Done")
