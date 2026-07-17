import py_compile, sys
try:
    py_compile.compile(r"C:\AMCTracker\tracker_multiwatch.py", doraise=True)
    print("OK: no syntax errors")
except py_compile.PyCompileError as e:
    print(f"FAIL: {e}")
    sys.exit(1)
