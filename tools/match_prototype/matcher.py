"""分层地图形状匹配引擎（原型 / 离线验证用）。

思路
----
玩家上传一张「侧门形状」局部图 -> 用 ORB 特征点匹配，
在地图数据目录树上 **逐层贪心** 筛选（形状 -> 侧门位置 -> 路线...），
最终命中一张叶子小抄图，并返回每一层的决策与置信度。

不联网、不 OCR、不 AI。纯经典 CV（OpenCV ORB + BFMatcher）。

目录树深度是自动适配的：无论形状下还有几层子文件夹，
引擎都从 MAP_ROOTS 出发，每一层在「当前候选子目录」里挑匹配分最高的分支，
直到某层没有子目录（到达叶子层），再在叶子图里挑最像的一张。
"""

from __future__ import annotations

import os
from pathlib import Path

import cv2
import numpy as np

IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp")


class ShapeMatcher:
    def __init__(self, map_roots, preprocess: str = "gray", max_features: int = 2000):
        if isinstance(map_roots, (str, Path)):
            map_roots = [str(map_roots)]
        self.map_roots = [str(p) for p in map_roots]
        self.preprocess = preprocess
        self.det = cv2.ORB_create(max_features)
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    # ---------- 图像与特征 ----------
    def _load_gray(self, path: str):
        # 注意：cv2.imread 在 Windows 上对含非 ASCII / 特殊 Unicode（如 ┏ ▃▃）
        # 的路径会静默失败，改用 numpy 读字节 + imdecode 绕过路径限制。
        try:
            with open(path, "rb") as f:
                buf = np.frombuffer(f.read(), dtype=np.uint8)
        except OSError:
            return None
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if img is None:
            return None
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        if self.preprocess == "binary":
            _, g = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        elif self.preprocess == "canny":
            g = cv2.Canny(g, 50, 150)
        elif self.preprocess == "blur":
            g = cv2.GaussianBlur(g, (3, 3), 0)
        return g

    def _detect(self, gray):
        if gray is None:
            return None, None
        kp, des = self.det.detectAndCompute(gray, None)
        return kp, des

    # ---------- 相似度 ----------
    @staticmethod
    def _score(des_q, des_t):
        """归一化匹配得分：good matches / min(两图关键点数量)，落在 0..1。

        用 min 归一化可避免「大图关键点多 => 分数虚高」的偏差，
        让不同尺寸/比例的图更公平地比较。
        """
        if des_q is None or des_t is None:
            return 0.0
        nq, nt = len(des_q), len(des_t)
        if nq == 0 or nt == 0:
            return 0.0
        try:
            matches = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(des_q, des_t)
        except cv2.error:
            return 0.0
        norm = min(nq, nt)
        return len(matches) / norm

    # ---------- 目录树遍历 ----------
    def _subdirs(self, d: str):
        return [os.path.join(d, n) for n in os.listdir(d) if os.path.isdir(os.path.join(d, n))]

    def _list_images(self, d: str):
        return [os.path.join(d, n) for n in os.listdir(d) if n.lower().endswith(IMG_EXTS)]

    def _branch_best_score(self, des_q, folder: str):
        """folder 下（递归）所有图片与 query 的最高匹配分。

        取该分支内「最像」的一张的得分，作为整条分支的代表分，
        避免「代表图选错」导致的分支误判。
        """
        best = 0.0
        for r, _, fs in os.walk(folder):
            for f in fs:
                if not f.lower().endswith(IMG_EXTS):
                    continue
                g = self._load_gray(os.path.join(r, f))
                _, des_t = self._detect(g)
                s = self._score(des_q, des_t)
                if s > best:
                    best = s
        return best

    # ---------- 主匹配 ----------
    def match(self, query_path: str, topk: int = 3):
        g = self._load_gray(query_path)
        _, des_q = self._detect(g)
        if des_q is None:
            raise ValueError(f"无法读取或提取特征: {query_path}")

        current = list(self.map_roots)
        decisions = []

        # 逐层贪心：每层在候选子目录里挑分支最佳分最高者进入
        while True:
            sub = [p for d in current for p in self._subdirs(d)]
            if not sub:
                break  # 没有子目录 => 到达叶子层
            ranked = []
            for d in sub:
                s = self._branch_best_score(des_q, d)
                ranked.append((d, round(s, 4)))
            ranked.sort(key=lambda x: -x[1])
            chosen, score = ranked[0]
            decisions.append({
                "level": len(decisions),
                "chosen": chosen,
                "score": score,
                "top": ranked[:topk],
            })
            current = [chosen]

        # 叶子层：在 current 各目录里挑最像的叶子小抄图
        leaf_ranked = []
        for d in current:
            for img in self._list_images(d):
                g = self._load_gray(img)
                _, des_t = self._detect(g)
                s = self._score(des_q, des_t)
                leaf_ranked.append((img, round(s, 4)))
        leaf_ranked.sort(key=lambda x: -x[1])

        hit = leaf_ranked[0][0] if leaf_ranked else None
        score = leaf_ranked[0][1] if leaf_ranked else 0.0

        return {
            "query": query_path,
            "hit": hit,
            "score": score,
            "decisions": decisions,
            "leaf_top": leaf_ranked[:topk],
        }
