"""Run before pushing:  python scripts/check_ownership.py track1   (or track2 / track3)
Lists every file you changed that is not yours. Touching only your own files means merges never conflict."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rules = json.loads((ROOT / "docs" / "OWNERSHIP.json").read_text())

if len(sys.argv) != 2 or sys.argv[1] not in ("track1", "track2", "track3"):
    sys.exit("usage: python scripts/check_ownership.py track1|track2|track3")
track = sys.argv[1]


def git(*args: str) -> list[str]:
    out = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    return [x for x in out.stdout.splitlines() if x]


base = "origin/main" if git("rev-parse", "--verify", "origin/main") else "main"
changed = set(git("diff", "--name-only", f"{base}...HEAD")) | set(git("diff", "--name-only")) | set(
    git("ls-files", "--others", "--exclude-standard"))

bad = []
for f in sorted(changed):
    if f in rules["frozen"]:
        bad.append((f, "FROZEN: only the integrator may change this"))
    elif not any(f.startswith(p) for p in rules[track]):
        bad.append((f, "belongs to another track"))

if bad:
    print(f"Files outside {track}:")
    for f, why in bad:
        print(f"  {f}  ->  {why}")
    print("\nUndo them with: git checkout <base> -- <file>   (or ask the integrator)")
    sys.exit(1)
print(f"OK: every changed file belongs to {track}.")
