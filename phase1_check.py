import sys
import struct
import requests

print("=== PHASE 1 RUNTIME TEST ===")
print("Python:", sys.version.split()[0])
print("Architecture:", f"{struct.calcsize('P') * 8}-bit")
print("Executable:", sys.executable)
print("Requests:", requests.__version__)
print("Venv:", sys.prefix != sys.base_prefix)

try:
    response = requests.get(
        "https://www.python.org",
        timeout=10,
    )

    print("HTTP Status:", response.status_code)

    checks = {
        "python_3_13": sys.version_info[:2] == (3, 13),
        "architecture_64": struct.calcsize("P") * 8 == 64,
        "venv_active": sys.prefix != sys.base_prefix,
        "requests_ok": requests.__version__ == "2.34.2",
        "http_ok": response.status_code == 200,
    }

    print()
    for name, result in checks.items():
        print(f"{name}: {'PASS' if result else 'FAIL'}")

    print()
    if all(checks.values()):
        print("PHASE1_RUNTIME_TEST=PASS")
    else:
        print("PHASE1_RUNTIME_TEST=FAIL")

except Exception as exc:
    print()
    print("Network Error:", type(exc).__name__, str(exc))
    print("PHASE1_RUNTIME_TEST=FAIL")
