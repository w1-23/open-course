"""Forward to the equation-number checker in the repository root.

Same reason as scripts/check_refs.py: the contract names the scripts/ path.
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import check_eqno  # noqa: E402

if __name__ == "__main__":
    sys.exit(check_eqno.main())
