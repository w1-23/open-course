"""Download every external source the textbook quotes into ``source/``.

Environment note (measured, not guessed): in this harness ``curl.exe`` and
``Invoke-WebRequest`` both die during TLS setup with
``schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS``, and the
Electron browser provider is unavailable from a background Python process.
Python ``requests`` (OpenSSL + certifi) is the only working HTTPS client, and
plain ``http://`` works for both.  So everything goes through requests here.

Usage:  python download.py            # download what is missing
        python download.py --force    # re-download everything
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import fitz
import requests

ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(ROOT, "source")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# (subdir, filename, url, min_bytes)
ITEMS = [
    # ---- classical RL textbook (MIT Press, free PDF; https cert fails here)
    ("book", "RLbook2020.pdf",
     "http://incompleteideas.net/book/RLbook2020.pdf", 60_000_000),

    # ---- surveys
    ("papers", "2407.16216_rl-for-llm-post-training-survey.pdf",
     "https://arxiv.org/pdf/2407.16216v4", 1_000_000),
    ("papers", "2509.16679_rl-meets-llms-survey.pdf",
     "https://arxiv.org/pdf/2509.16679v1", 900_000),
    ("papers", "1811.12560_intro-to-deep-rl.pdf",
     "https://arxiv.org/pdf/1811.12560v2", 1_000_000),

    # ---- foundational algorithms
    ("papers", "1707.06347_ppo.pdf", "https://arxiv.org/pdf/1707.06347v2", 2_000_000),
    ("papers", "1706.03741_christiano-rlhf.pdf",
     "https://arxiv.org/pdf/1706.03741v4", 2_000_000),
    ("papers", "2203.02155_instructgpt.pdf", "https://arxiv.org/pdf/2203.02155v1", 1_100_000),
    ("papers", "2305.18290_dpo.pdf", "https://arxiv.org/pdf/2305.18290v3", 1_000_000),
    ("papers", "2402.03300_deepseekmath-grpo.pdf", "https://arxiv.org/pdf/2402.03300v3", 1_500_000),
    ("papers", "2006.04779_cql.pdf", "https://arxiv.org/pdf/2006.04779v3", 1_000_000),
    ("papers", "1509.02971_ddpg.pdf", "https://arxiv.org/pdf/1509.02971v6", 600_000),
    ("papers", "1801.01290_sac.pdf", "https://arxiv.org/pdf/1801.01290v2", 800_000),
    ("papers", "1602.01783_a3c.pdf", "https://arxiv.org/pdf/1602.01783v2", 1_000_000),
    ("papers", "1509.06461_double-dqn.pdf", "https://arxiv.org/pdf/1509.06461v3", 500_000),
    ("papers", "1511.06581_dueling-dqn.pdf", "https://arxiv.org/pdf/1511.06581v3", 500_000),
    ("papers", "1511.05952_prioritized-replay.pdf",
     "https://arxiv.org/pdf/1511.05952v4", 800_000),
    ("papers", "1712.01815_alphazero.pdf", "https://arxiv.org/pdf/1712.01815v1", 600_000),
    ("papers", "1911.08265_muzero.pdf", "https://arxiv.org/pdf/1911.08265v2", 2_000_000),
    ("papers", "1802.01561_apex.pdf", "https://arxiv.org/pdf/1802.01561v3", 1_000_000),

    # ---- long-form notes / course pages (HTML)
    ("pages", "spinningup_rl_intro.html",
     "https://spinningup.openai.com/en/latest/spinningup/rl_intro.html", 40_000),
    ("pages", "spinningup_rl_intro2.html",
     "https://spinningup.openai.com/en/latest/spinningup/rl_intro2.html", 25_000),
    ("pages", "spinningup_rl_intro3.html",
     "https://spinningup.openai.com/en/latest/spinningup/rl_intro3.html", 40_000),
    ("pages", "spinningup_vpg.html",
     "https://spinningup.openai.com/en/latest/algorithms/vpg.html", 30_000),
    ("pages", "spinningup_ppo.html",
     "https://spinningup.openai.com/en/latest/algorithms/ppo.html", 30_000),
    ("pages", "spinningup_sac.html",
     "https://spinningup.openai.com/en/latest/algorithms/sac.html", 30_000),
    ("pages", "spinningup_td3.html",
     "https://spinningup.openai.com/en/latest/algorithms/td3.html", 20_000),
    ("pages", "spinningup_trpo.html",
     "https://spinningup.openai.com/en/latest/algorithms/trpo.html", 20_000),
    ("pages", "spinningup_ddpg.html",
     "https://spinningup.openai.com/en/latest/algorithms/ddpg.html", 20_000),
    ("pages", "weng_policy_gradient.html",
     "https://lilianweng.github.io/posts/2018-04-08-policy-gradient/", 60_000),
    ("pages", "weng_reward_hacking.html",
     "https://lilianweng.github.io/posts/2024-11-28-reward-hacking/", 40_000),
    ("pages", "cs224r_index.html", "https://cs224r.stanford.edu/", 10_000),
    ("pages", "cs285_index.html", "https://rail.eecs.berkeley.edu/deeprlcourse/", 10_000),
    ("pages", "awesome_rlhf_readme.md",
     "https://raw.githubusercontent.com/opendilab/awesome-RLHF/main/README.md", 5_000),
]

HEADERS = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"}


def fetch(url: str, tries: int = 4) -> bytes:
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=180, allow_redirects=True)
            if r.status_code == 200 and r.content:
                return r.content
            last = f"HTTP {r.status_code}"
        except Exception as exc:                      # noqa: BLE001 - report and retry
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(1.5 * (i + 1))
    raise RuntimeError(last or "unknown error")


def pdf_to_text(pdf_path: str, txt_path: str) -> int:
    doc = fitz.open(pdf_path)
    parts = []
    for page in doc:
        parts.append(page.get_text("text"))
    doc.close()
    text = "\n".join(parts)
    with open(txt_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return len(text)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    ok, skipped, failed = [], [], []
    for sub, name, url, min_bytes in ITEMS:
        out_dir = os.path.join(SOURCE, sub)
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, name)
        if os.path.exists(path) and os.path.getsize(path) >= min_bytes and not args.force:
            skipped.append(name)
            continue
        t0 = time.time()
        try:
            data = fetch(url)
        except Exception as exc:                      # noqa: BLE001
            failed.append((name, str(exc)[:160]))
            print(f"FAIL {name:52} {str(exc)[:70]}", flush=True)
            continue
        if len(data) < min_bytes:
            failed.append((name, f"suspiciously small: {len(data)} bytes"))
            print(f"FAIL {name:52} small {len(data)}", flush=True)
            continue
        with open(path, "wb") as fh:
            fh.write(data)
        ok.append((name, len(data), time.time() - t0))
        print(f"OK   {name:52} {len(data)/1048576:7.2f} MB  "
              f"{time.time()-t0:5.1f}s", flush=True)

        if name.lower().endswith(".pdf"):
            txt = os.path.join(SOURCE, "text", os.path.splitext(name)[0] + ".txt")
            n = pdf_to_text(path, txt)
            print(f"     text -> {os.path.basename(txt)} ({n/1024:.0f} KB)", flush=True)

    print(f"\nnew {len(ok)} | cached {len(skipped)} | failed {len(failed)}")
    for name, err in failed:
        print(f"  FAILED {name}: {err}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
