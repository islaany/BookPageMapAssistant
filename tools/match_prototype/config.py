"""匹配原型配置（离线验证用，不属于 Android App）。

路径约定：本文件位于 tools/match_prototype/，项目根为其上两级。
"""

from pathlib import Path

# 项目根目录：tools/match_prototype -> ../../
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# 地图数据主目录列表（每个副本/难度一个）。
# 匹配引擎只在这些目录下递归查找小抄叶子图，
# 不会扫到 data/ 根的占位目录(reference/screenshots)与教学图。
# 后续若新增其他副本/难度，往这个列表里追加即可。
MAP_ROOTS = [
    str(PROJECT_ROOT / "data" / "厄运困难（超清4k，宝藏房，展十版）全棺版12.8"),
]

# 默认预处理方式：gray | binary | canny | blur
#  - gray  : 直接灰度（默认，最快）
#  - binary: Otsu 二值化，突出黑白形状
#  - canny : Canny 边缘，只保留轮廓（适合"侧门形状"这类线条图）
#  - blur  : 轻度高斯模糊去噪
DEFAULT_PREPROCESS = "gray"
