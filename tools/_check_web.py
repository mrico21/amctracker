import py_compile
import sys
from pathlib import Path

web_root = Path(r"C:\AMCTracker\web")
files = sorted(web_root.rglob("*.py"))
failed = 0

for f in files:
    try:
        py_compile.compile(str(f), doraise=True)
        print(f"OK   {f.relative_to(web_root.parent)}")
    except py_compile.PyCompileError as e:
        print(f"FAIL {f.relative_to(web_root.parent)}: {e}")
        failed += 1

print(f"\n{len(files)} files checked, {failed} failed")
sys.exit(1 if failed else 0)
