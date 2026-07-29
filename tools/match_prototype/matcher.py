"""分层地图形状匹配引擎（原型 / 离线验证用）。

思路
----
玩家上传一张「侧门形状」局部图 -> 用经典 CV 特征匹配或形状轮廓匹配，
在地图数据目录树上 **逐层贪心** 筛选（形状 -> 侧门位置 -> 路线...），
最终命中一张叶子小抄图，并返回每一层的决策与置信度。

不联网、不 OCR、不 AI。支持两种模式：
- orb：ORB 特征点 + BFMatcher（默认，适合风格接近的图）
- shape：二值轮廓 + Hu 矩（对「灰度小地图 vs 彩色小抄」更鲁棒）

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
    def __init__(
        self,
        map_roots,
        preprocess: str = "gray",
        mode: str = "orb",
        max_features: int = 2000,
        min_features: int = 10,
    ):
        if isinstance(map_roots, (str, Path)):
            map_roots = [str(map_roots)]
        self.map_roots = [str(p) for p in map_roots]
        self.preprocess = preprocess
        self.mode = mode.lower()
        self.min_features = min_features
        self.det = cv2.ORB_create(max_features)
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)

    # ---------- 图像加载与预处理 ----------
    def _load_color(self, path: str):
        # 注意：cv2.imread 在 Windows 上对含非 ASCII / 特殊 Unicode（如 ┏ ▃▃）
        # 的路径会静默失败，改用 numpy 读字节 + imdecode 绕过路径限制。
        try:
            with open(path, "rb") as f:
                buf = np.frombuffer(f.read(), dtype=np.uint8)
        except OSError:
            return None
        return cv2.imdecode(buf, cv2.IMREAD_COLOR)

    def _load_gray(self, path: str):
        img = self._load_color(path)
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

    def _binary_silhouette(self, path: str):
        """返回二值轮廓图（用于 shape 模式）。"""
        img = self._load_color(path)
        if img is None:
            return None
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # 小地图是亮走廊/暗背景；小抄是彩色路线。统一用 Otsu 取前景。
        _, binary = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        # 小地图情况：前景是亮走廊；如果前景面积反而更大（小抄文字多），取反。
        fg_ratio = np.count_nonzero(binary) / binary.size
        if fg_ratio > 0.6:
            binary = cv2.bitwise_not(binary)
        # 去噪 + 闭运算连接断裂的走廊
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
        return binary

    # ---------- 特征 / 形状描述 ----------
    def _detect(self, gray):
        if gray is None:
            return None, None
        kp, des = self.det.detectAndCompute(gray, None)
        return kp, des

    def _hu_descriptor(self, binary):
        """从二值图计算 Hu 矩描述子。"""
        if binary is None:
            return None
        moments = cv2.moments(binary)
        hu = cv2.HuMoments(moments).flatten()
        # 对数变换，拉近数量级
        hu = np.sign(hu) * np.log10(np.abs(hu) + 1e-10)
        return hu

    # ---------- 相似度 ----------
    @staticmethod
    def _score(des_q, des_t, min_features: int = 10):
        """ORB 归一化匹配得分：good matches / min(两图关键点数量)，落在 0..1。

        用 min 归一化可避免「大图关键点多 => 分数虚高」的偏差，
        让不同尺寸/比例的图更公平地比较。
        """
        if des_q is None or des_t is None:
            return 0.0
        nq, nt = len(des_q), len(des_t)
        if nq < min_features or nt < min_features:
            return 0.0
        try:
            matches = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(des_q, des_t)
        except cv2.error:
            return 0.0
        norm = min(nq, nt)
        return len(matches) / norm

    def _shape_score(self, hu_q, hu_t):
        """Hu 矩形状相似度，范围 (0,1]，1 为完全相同。"""
        if hu_q is None or hu_t is None:
            return 0.0
        dist = np.linalg.norm(hu_q - hu_t)
        return 1.0 / (1.0 + dist)

    # ---------- 目录树遍历 ----------
    def _subdirs(self, d: str):
        return [os.path.join(d, n) for n in os.listdir(d) if os.path.isdir(os.path.join(d, n))]

    def _list_images(self, d: str):
        return [os.path.join(d, n) for n in os.listdir(d) if n.lower().endswith(IMG_EXTS)]

    def _branch_best_score(self, query_desc, folder: str):
        """folder 下（递归）所有图片与 query 的最高匹配分。

        取该分支内「最像」的一张的得分，作为整条分支的代表分，
        避免「代表图选错」导致的分支误判。
        """
        best = 0.0
        for r, _, fs in os.walk(folder):
            for f in fs:
                if not f.lower().endswith(IMG_EXTS):
                    continue
                path = os.path.join(r, f)
                if self.mode == "shape":
                    bin_t = self._binary_silhouette(path)
                    hu_t = self._hu_descriptor(bin_t)
                    s = self._shape_score(query_desc, hu_t)
                else:
                    g = self._load_gray(path)
                    _, des_t = self._detect(g)
                    s = self._score(des_t, query_desc, self.min_features)
                if s > best:
                    best = s
        return best

    # ---------- 主匹配 ----------
    def match(self, query_path: str, topk: int = 3):
        if self.mode == "shape":
            bin_q = self._binary_silhouette(query_path)
            query_desc = self._hu_descriptor(bin_q)
            if query_desc is None:
                raise ValueError(f"无法读取或提取形状特征: {query_path}")
        else:
            g = self._load_gray(query_path)
            _, query_desc = self._detect(g)
            if query_desc is None:
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
                s = self._branch_best_score(query_desc, d)
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
                if self.mode == "shape":
                    bin_t = self._binary_silhouette(img)
                    hu_t = self._hu_descriptor(bin_t)
                    s = self._shape_score(query_desc, hu_t)
                else:
                    g = self._load_gray(img)
                    _, des_t = self._detect(g)
                    s = self._score(des_t, query_desc, self.min_features)
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
