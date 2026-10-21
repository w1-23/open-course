"""转发脚本：作者按契约调用 `python scripts\\check_math.py`，实现在仓库根。"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import check_math  # noqa: E402

if __name__ == "__main__":
    sys.exit(check_math.main())
