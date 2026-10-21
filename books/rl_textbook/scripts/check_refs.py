"""Forward to the cross-reference checker in the repository root.

The checks live at the top level (they import config and the chapter table);
this shim exists because the authoring contract tells authors to run
`python scripts\\check_refs.py --only N`.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import check_refs  # noqa: E402

if __name__ == "__main__":
    sys.exit(check_refs.main())
