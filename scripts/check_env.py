"""Version drift detector. Run before you start and before you push.
Compares your machine with the locked versions and tells you exactly how to fix any difference."""
import importlib.metadata as md
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
problems: list[str] = []


def norm(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


# Python version
if sys.version_info[:2] not in ((3, 11), (3, 12), (3, 13)):
    problems.append(f"Python {sys.version.split()[0]} found. Use Python 3.11, 3.12 or 3.13 (all tested).")

# Python packages vs lock
installed = {norm(d.metadata["Name"]): d.version for d in md.distributions()}
for line in (ROOT / "backend" / "requirements.lock.txt").read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    spec, _, marker = line.partition(";")
    if "win32" in marker and sys.platform != "win32":
        continue
    name, _, want = spec.strip().partition("==")
    have = installed.get(norm(name))
    if have is None:
        problems.append(f"Missing package {name}=={want}")
    elif have != want:
        problems.append(f"{name}: installed {have}, locked {want}")

# Node
try:
    out = subprocess.run(["node", "--version"], capture_output=True, text=True, shell=(sys.platform == "win32")).stdout.strip()
    major, minor = (int(x) for x in out.lstrip("v").split(".")[:2])
    if (major, minor) < (20, 19):
        problems.append(f"Node {out} found. Use Node 22 or newer (minimum 20.19).")
except Exception:
    problems.append("Node.js not found. Install Node 22 or newer.")

if not (ROOT / "frontend" / "node_modules").exists():
    problems.append("frontend/node_modules missing. Run: cd frontend ; npm ci")

if problems:
    print("ENVIRONMENT PROBLEMS:")
    for p in problems:
        print(" -", p)
    print("\nFix: run scripts\\setup.ps1 again. Do NOT run pip install <package> or npm install <package>.")
    sys.exit(1)
print("Environment OK: Python, packages and Node all match the lock.")
