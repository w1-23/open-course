"""CH07 maze: 复算第 7.1.2 节迷宫的最短路径长度。

问题
----
`content/ch07.md:49` 与图 7-2 的说明称"最优路径是 13 步，多出的两步来自 ε=0.1 的探索"。
这个 13 原先无法核实（S&B 正文只给迷宫插图，不给最短路径长度）。本脚本按**图 7-2 实际
使用的那张迷宫**（与 `figures/ch07_figs.py` 的 ROWS/COLS/WALLS/START/GOAL 完全一致）
做 BFS，把 13 变成可复算的数字。

做法
----
1. 网格 9 行 × 6 列、7 个障碍，共 47 个可通行状态（54 − 7），与正文一致。
2. 四个动作（上/下/左/右）确定性移动；撞墙或进障碍则停在原地（S&B Example 8.1 的规则）。
3. BFS 求最少移动次数，进入目标格的那一步计入。

附带说明
--------
S&B Figure 8.2 原图是 6 行 × 9 列、障碍位于 (1,2)(2,2)(3,2)(0,7)(1,7)(2,7)(4,5)、
S=(2,0)、G=(0,8) 的另一张迷宫。按那张图转录做 BFS 得到 **14** 步，不是 13。
本书的图 7-2 用的是上文"按例 8.1 规模自建"的 9×6 迷宫（最优 13），正文已据此写明
"按 S&B 例 8.1 的规模自建，不是逐格复刻其插图"，以免把两个数字混用。

运行
----
    python review/reproductions/CH07-MAZE_maze_bfs.py

退出码 0 表示可通行状态数 = 47 且最短路径 = 13（与书稿一致），否则为 1。
"""

from __future__ import annotations

from collections import deque

# 与 figures/ch07_figs.py 的定义逐字一致（行 88-91）。
ROWS, COLS = 9, 6
WALLS = {(1, 1), (2, 1), (3, 1), (1, 3), (2, 3), (3, 3), (6, 2)}
START, GOAL = (8, 0), (0, 5)
ACTS = ((-1, 0), (1, 0), (0, -1), (0, 1))

CLAIMED = 13          # content/ch07.md:49 声称的最优路径长度
CLAIMED_STATES = 47   # 正文称"去掉 7 个障碍格后剩 47 个状态"


def bfs():
    dist = {START: 0}
    parent = {START: None}
    queue = deque([START])
    while queue:
        state = queue.popleft()
        if state == GOAL:
            break
        r, c = state
        for dr, dc in ACTS:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < ROWS and 0 <= nc < COLS) or (nr, nc) in WALLS:
                nr, nc = r, c          # 撞墙/越界：停在原地
            nxt = (nr, nc)
            if nxt not in dist:
                dist[nxt] = dist[state] + 1
                parent[nxt] = state
                queue.append(nxt)
    path, node = [], GOAL
    while node is not None:
        path.append(node)
        node = parent.get(node)
    return dist.get(GOAL), list(reversed(path))


def main() -> int:
    free = ROWS * COLS - len(WALLS)
    d, path = bfs()
    print(f"网格 {ROWS}x{COLS}，障碍 {len(WALLS)} 个，可通行状态 {free} 个")
    print(f"起点 S={START}  终点 G={GOAL}")
    print(f"最短路径长度 = {d}  （书稿声称 {CLAIMED}）")
    print("一条最优路径：" + " -> ".join(f"({r},{c})" for r, c in path))
    if free != CLAIMED_STATES:
        print(f"[FAIL] 可通行状态数应为 {CLAIMED_STATES}，实得 {free}")
        return 1
    if d != CLAIMED:
        print(f"[FAIL] 最短路径 {d} != 声称 {CLAIMED}")
        return 1
    print("[OK] 与书稿一致（47 状态 / 13 步）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
