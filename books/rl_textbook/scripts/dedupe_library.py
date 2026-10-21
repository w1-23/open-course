"""清理 source/library/ 下"同一 PDF 被登记成两个 key"的重复目录。

判定：读每个 meta.yaml 的 path 字段，同一 path 只保留一个目录，优先保留
key 出现在 build_library.SOURCES 里的那个（其余视为早期 discover 的遗留）。
"""
from __future__ import annotations

import os
import shutil
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "source", "library")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_library as bl  # noqa: E402


def main(apply: bool) -> int:
    groups: dict[str, list[str]] = {}
    for name in sorted(os.listdir(LIB)):
        d = os.path.join(LIB, name)
        if not os.path.isdir(d):
            continue
        meta_path = os.path.join(d, "meta.yaml")
        if not os.path.exists(meta_path):
            print(f"[warn] 无 meta.yaml：{name}")
            continue
        try:
            with open(meta_path, encoding="utf-8") as fh:
                meta = yaml.safe_load(fh) or {}
        except Exception as exc:
            print(f"[warn] meta.yaml 解析失败：{name}（{exc.__class__.__name__}）")
            continue
        groups.setdefault(str(meta.get("path") or name), []).append(name)

    removed = 0
    for path, keys in groups.items():
        if len(keys) == 1:
            continue
        keep = next((k for k in keys if k in bl.SOURCES), sorted(keys)[0])
        for k in keys:
            if k == keep:
                continue
            print(f"{'删除' if apply else '待删'} {k}  （与 {keep} 同一文件：{path}）")
            if apply:
                shutil.rmtree(os.path.join(LIB, k), ignore_errors=True)
                removed += 1

    print(f"\n重复组 {sum(1 for v in groups.values() if len(v) > 1)} 个，"
          f"{'已删' if apply else '将删'} {removed if apply else '若干'} 个目录")
    return 0


if __name__ == "__main__":
    sys.exit(main("--apply" in sys.argv))
