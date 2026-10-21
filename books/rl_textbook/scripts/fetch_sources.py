"""W0A：按 v3.1 的缺口清单补抓原始文献。

只抓**公开可获取**的来源（arXiv / 作者公开页 / 官方文档）。
版权书（Puterman 等）不下载，只记 source/library/PENDING.yaml。

命名约定：文件名 = `<arxiv_id>_<短名>.pdf` 或 `<短名>.pdf`（无 arXiv 号时），
与 build_library.py 的 key 推断一致（去掉 .pdf 即 key）。

用法：
    python scripts/fetch_sources.py            # 抓全部
    python scripts/fetch_sources.py --group P0 # 只抓 P0
    python scripts/fetch_sources.py --force    # 覆盖已存在文件
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "source")
UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0 Safari/537.36"
    )
}

# (group, file, url, min_bytes)
ITEMS = [
    # ---------------- P0：支撑已确认勘误
    ("P0", "1506.02438_gae.pdf", "https://arxiv.org/pdf/1506.02438", 300_000),
    ("P0", "1502.05477_trpo.pdf", "https://arxiv.org/pdf/1502.05477", 300_000),
    ("P0", "1609.05140_option-critic.pdf", "https://arxiv.org/pdf/1609.05140", 300_000),
    ("P0", "1904.07272_bandit-algorithms.pdf", "https://arxiv.org/pdf/1904.07272", 1_000_000),
    ("P0", "1707.02038_thompson-sampling.pdf", "https://arxiv.org/pdf/1707.02038", 300_000),
    ("P0", "1812.02648_deadly-triad.pdf", "https://arxiv.org/pdf/1812.02648", 200_000),
    # ---------------- P1：算法基准
    ("P1", "1312.5602_dqn.pdf", "https://arxiv.org/pdf/1312.5602", 300_000),
    ("P1", "1802.09477_td3.pdf", "https://arxiv.org/pdf/1802.09477", 300_000),
    ("P1", "1812.02900_bcq.pdf", "https://arxiv.org/pdf/1812.02900", 300_000),
    ("P1", "2110.06169_iql.pdf", "https://arxiv.org/pdf/2110.06169", 300_000),
    ("P1", "2106.01345_decision-transformer.pdf", "https://arxiv.org/pdf/2106.01345", 300_000),
    ("P1", "2004.07219_d4rl.pdf", "https://arxiv.org/pdf/2004.07219", 300_000),
    ("P1", "2005.01643_offline-rl-tutorial.pdf", "https://arxiv.org/pdf/2005.01643", 300_000),
    ("P1", "1805.12114_pets.pdf", "https://arxiv.org/pdf/1805.12114", 300_000),
    ("P1", "1906.08253_mbpo.pdf", "https://arxiv.org/pdf/1906.08253", 300_000),
    ("P1", "1912.01603_dreamer.pdf", "https://arxiv.org/pdf/1912.01603", 300_000),
    ("P1", "1706.02275_maddpg.pdf", "https://arxiv.org/pdf/1706.02275", 300_000),
    ("P1", "1803.11485_qmix.pdf", "https://arxiv.org/pdf/1803.11485", 300_000),
    ("P1", "1705.10528_cpo.pdf", "https://arxiv.org/pdf/1705.10528", 300_000),
    ("P1", "2501.12948_deepseek-r1.pdf", "https://arxiv.org/pdf/2501.12948", 300_000),
    ("P1", "2210.03629_react.pdf", "https://arxiv.org/pdf/2210.03629", 300_000),
    ("P1", "2303.11366_reflexion.pdf", "https://arxiv.org/pdf/2303.11366", 200_000),
    ("P1", "2309.02427_toolllm.pdf", "https://arxiv.org/pdf/2309.02427", 300_000),
    ("P1", "1612.00796_ewc.pdf", "https://arxiv.org/pdf/1612.00796", 300_000),
    ("P1", "1011.0686_dagger.pdf", "https://arxiv.org/pdf/1011.0686", 300_000),
    # ---------------- P2：争议与延伸（只进研究框）
    ("P2", "2503.14476_dapo.pdf", "https://arxiv.org/pdf/2503.14476", 300_000),
    ("P2", "2503.20783_dr-grpo.pdf", "https://arxiv.org/pdf/2503.20783", 300_000),
    ("P2", "2507.18071_gspo.pdf", "https://arxiv.org/pdf/2507.18071", 300_000),
    ("P2", "2508.03680_agent-lightning.pdf", "https://arxiv.org/pdf/2508.03680", 300_000),
    # 无 arXiv 号但公开可得的原始材料
    ("P0", "sutton1988_td.pdf",
     "http://incompleteideas.net/papers/sutton-88.pdf", 200_000),
    ("P0", "baird1995_residual-algorithms.pdf",
     "https://www.cs.cmu.edu/afs/cs/project/jair/pub/volume4/baird95a.pdf", 150_000),
    ("P0", "precup2000_between-mdps-smdps.pdf",
     "https://people.cs.umass.edu/~barto/courses/cs687/precup-sutton-singh-2000.pdf", 150_000),
]


def fetch(url: str, path: str, min_bytes: int, force: bool) -> str:
    if os.path.exists(path) and os.path.getsize(path) >= min_bytes and not force:
        return "cached"
    last = ""
    for i in range(4):
        try:
            r = requests.get(url, headers=UA, timeout=180, allow_redirects=True)
            if r.status_code != 200:
                last = f"HTTP {r.status_code}"
                time.sleep(1.5 * (i + 1))
                continue
            body = r.content
            if len(body) < min_bytes:
                last = f"small {len(body)}"
                time.sleep(1.0)
                continue
            if body[:4] != b"%PDF":
                last = "not-pdf"
                time.sleep(1.0)
                continue
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(body)
            return f"OK {len(body) / 1e6:.2f}MB"
        except Exception as exc:
            last = f"{type(exc).__name__}"
            time.sleep(1.5 * (i + 1))
    return f"FAIL {last}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default=None, choices=["P0", "P1", "P2"])
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    ok = fail = 0
    failed = []
    for group, name, url, min_bytes in ITEMS:
        if args.group and group != args.group:
            continue
        path = os.path.join(SRC, "papers", name)
        t0 = time.time()
        res = fetch(url, path, min_bytes, args.force)
        print(f"{group} {res:22s} {name} ({time.time() - t0:.1f}s)")
        if res.startswith(("OK", "cached")):
            ok += 1
        else:
            fail += 1
            failed.append((name, url, res))
    print(f"\n成功 {ok} | 失败 {fail}")
    for name, url, res in failed:
        print(f"  FAILED {name}: {res}  <- {url}")
    if failed:
        with open(os.path.join(ROOT, "cache", "fetch_failed.txt"), "w",
                  encoding="utf-8") as f:
            for name, url, res in failed:
                f.write(f"{name}\t{url}\t{res}\n")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
