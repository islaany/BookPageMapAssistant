# 匹配引擎原型（第二阶段离线验证）

本目录是「书页笔记地图助手」第二阶段 **特征匹配** 的离线验证原型，**不写入 Android App**。

目标：在把算法搬进 App 之前，先验证「玩家上传一张侧门形状图 → 能否正确命中
`data/` 里对应的小抄图」。

## 目录结构

- `config.py`     路径与预处理配置（MAP_ROOTS 指向真实地图数据目录）
- `matcher.py`    核心：ORB 特征点匹配 + 自动适配目录深度的逐层贪心筛选
- `test_match.py` 批量/单图测试，输出命中路径、置信度、每层决策与候选
- `requirements.txt` 依赖（opencv-python==5.0.0, numpy）
- `samples/`     放你随机给的「只有侧门形状」的测试图（.gitkeep 占位，图片不进版本库）

## 运行

需要 Python 3.11+ 且已装 opencv-python / numpy（当前沙箱 cv2 5.0.0 已就绪）。

    cd tools/match_prototype
    python test_match.py --dir samples            # 测试 samples 下所有图
    python test_match.py --query samples/x.jpg    # 单张
    python test_match.py --preprocess canny       # 换预处理
    python test_match.py --topk 5                 # 输出 top5 候选

## 输出解读

- `命中`：引擎认为最像的小抄图路径
- `置信度(score)`：归一化匹配分 = good matches / min(两图关键点数)，0~1，越大越像
- `分层决策`：每一层选了哪个文件夹、分数多少、其他候选（用于判断哪一层开始跑偏）
- `叶子 top`：最终候选小抄图按分排序

## 调参方向（匹配度不好时）

- `--preprocess` 切换：gray(默认) / binary(Otsu 二值) / canny(只留轮廓) / blur(去噪)。
  「侧门形状」多为线条图，canny 往往更准。
- 后续可加：只截取上传图特定区域、轮廓骨架化、模板匹配兜底。

## 与 App 的关系

验证通过后，再把 `matcher.py` 的核心逻辑（ORB 匹配 + 分层决策）移植为 Android 侧
（OpenCV Android SDK），接上「上传截图」入口与「切换覆盖层图片」。
