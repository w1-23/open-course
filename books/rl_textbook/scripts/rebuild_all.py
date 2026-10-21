"""Rebuild every chapter whose markdown exists, one after another."""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
os.chdir(ROOT)

import config  # noqa: E402

for i, ch in enumerate(config.CHAPTERS, 1):
    md = os.path.join(config.CONTENT_DIR, ch["slug"] + ".md")
    if not os.path.exists(md):
        print(f"skip ch{i:02d}: no markdown")
        continue
    print(f"== ch{i:02d} {ch['slug']}", flush=True)
    proc = subprocess.run([sys.executable, "main.py", "--only", str(i)],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    for line in [ln for ln in (proc.stdout or "").splitlines() if ln.strip()][-3:]:
        print("   " + line)
    if proc.returncode != 0:
        print("   FAILED", proc.returncode)
        print((proc.stderr or "")[-600:])
