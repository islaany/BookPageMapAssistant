"""批量测试匹配引擎（离线验证用）。

用法
----
  python test_match.py --dir samples          # 测试 samples 下所有图
  python test_match.py --query samples/x.jpg  # 单张
  python test_match.py --preprocess canny     # 换预处理（gray/binary/canny/blur）
  python test_match.py --topk 5               # 输出 top5 候选

输出每张查询图的：命中小抄路径、置信度(score)、每一层决策与候选、叶子 top。
把 score 与候选排序贴给助手，即可判断匹配度好坏、决定要不要调算法。
"""

from __future__ import annotations

import argparse
from pathlib import Path

from config import MAP_ROOTS
from matcher import ShapeMatcher, IMG_EXTS


def main():
    ap = argparse.ArgumentParser(description="地图形状匹配离线测试")
    ap.add_argument("--query", help="单张查询图路径")
    ap.add_argument("--dir", default="samples", help="测试图目录（默认 samples）")
    ap.add_argument("--preprocess", default="gray",
                    choices=["gray", "binary", "canny", "blur"])
    ap.add_argument("--topk", type=int, default=3, help="每层/叶子输出前几名")
    args = ap.parse_args()

    matcher = ShapeMatcher(MAP_ROOTS, preprocess=args.preprocess)

    queries = []
    if args.query:
        queries = [args.query]
    else:
        d = Path(args.dir)
        queries = sorted(str(p) for p in d.rglob("*") if p.suffix.lower() in IMG_EXTS)

    if not queries:
        print(f"没有可测试的图片。把测试图放到 {args.dir}/ 或用 --query 指定。")
        return

    for q in queries:
        try:
            res = matcher.match(q, topk=args.topk)
        except Exception as e:
            print("=" * 70)
            print(f"[错误] {q}: {e}")
            continue
        print("=" * 70)
        print(f"查询 : {q}")
        print(f"命中 : {res['hit']}")
        print(f"置信度(score): {res['score']}")
        print("--- 分层决策 ---")
        for dec in res["decisions"]:
            lvl = dec["level"]
            # 只显示文件夹名，路径太长
            name = dec["chosen"].split("\\")[-1].split("/")[-1]
            print(f"  L{lvl} 选: {name}  (score={dec['score']})")
            for p, s in dec["top"][1:]:
                nm = p.split("\\")[-1].split("/")[-1]
                print(f"        候选: {nm}  (score={s})")
        print("--- 叶子 top ---")
        for p, s in res["leaf_top"]:
            nm = p.split("\\")[-1].split("/")[-1]
            print(f"    {s}  {nm}")


if __name__ == "__main__":
    main()
