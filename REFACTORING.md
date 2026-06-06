# FreeCell 纸牌识别系统 - 重构文档

## 重构概述

本次重构将纸牌识别系统从"点数+花色分离匹配"改为"整体模板匹配"，大幅简化了代码架构和模板管理。

### 核心变更

```
旧架构:
  卡片 → 提取点数 → Card_Rank_Images/ → 点数模板匹配
       → 提取花色 → Card_Suit_Images/ → 花色模板匹配
       → 合并结果

新架构:
  卡片 → 裁切左上角 → Card_Info_Templates/ → 整体模板匹配 → 直接得到点数+花色
```

---

## 架构变更

### 1. 提取模块 (`extract_numbers.py`)

**旧方案**: 两个独立的提取函数
- `extract_number()`: 轮廓检测提取点数区域
- `extract_suit_from_image()`: 点数锚定+限定搜索提取花色

**新方案**: 单一裁切函数
- `extract_info_region()`: 裁切卡片左上角（宽度25% × 高度100%）

```python
# 新方案 - 简单裁切
def extract_info_region(image_path):
    img = cv2.imread(image_path)
    h, w = img.shape[:2]
    crop_w = int(w * 0.25)
    region = img[0:h, 0:crop_w]
    return binarize(region)
```

### 2. 模板结构

**旧方案**: 两套独立模板
```
Card_Rank_Templates/set_1920x1080/    # 52个点数模板
  A_r_1.png, A_r_2.png, ...          # 命名: {rank}_{color}_{seq}.png

Card_Suit_Templates/set_1/            # 52个花色模板
  H_r_1.png, H_r_2.png, ...          # 命名: {suit}_{color}_{seq}.png
```

**新方案**: 单一整体模板
```
Card_Info_Templates/set_1920x1080/    # 52个整体模板
  AH.png, 2S.png, TC.png, ...        # 命名: {rank}{suit}.png
```

### 3. 匹配模块 (`match_numbers.py`)

**旧方案**: 分离匹配器
```python
rank_matcher = RankMatcher(rank_templates)
suit_matcher = SuitMatcher(suit_templates)
rank = rank_matcher.match_rank(image, color)
suit = suit_matcher.match_suit(image, color)
```

**新方案**: 整体匹配器
```python
matcher = CombinedCardMatcher(template_dir)
result = matcher.match_card(info_image)
# result = {'rank': 'A', 'suit': 'H', 'confidence': 100.0}
```

---

## 新增组件

### CombinedTemplateManager

整体模板管理器，从单一目录加载 `{rank}{suit}.png` 格式的模板。

```python
class CombinedTemplateManager:
    """模板文件命名规则: {rank}{suit}.png (如 AH.png, 2S.png, TC.png)"""
    
    def __init__(self, template_dir: str):
        self.templates: Dict[str, List[Tuple[np.ndarray, str]]] = {'_r': [], '_b': []}
        self._load()
```

### CombinedCardMatcher

整体卡片匹配器，一次匹配同时得到点数和花色。

```python
class CombinedCardMatcher:
    def match_card(self, info_image: np.ndarray) -> Dict:
        """
        返回: {
            'rank': str,        # 点数 (A/2/.../T/J/Q/K)
            'suit': str,        # 花色 (H/S/D/C)
            'confidence': float  # 置信度 (0-100)
        }
        """
```

### CombinedTemplateCache

模板缓存，同一模板集只加载一次。

```python
matcher1 = CombinedCardMatcher('Card_Info_Templates/set_1920x1080')  # 加载模板
matcher2 = CombinedCardMatcher('Card_Info_Templates/set_1920x1080')  # 使用缓存
```

---

## API 变更

### 新增 API

| 函数 | 说明 |
|------|------|
| `process_all_cards_combined(template_dir)` | 使用整体模板批量处理 |
| `CombinedCardMatcher(template_dir)` | 整体匹配器 |
| `CombinedTemplateManager(template_dir)` | 整体模板管理器 |

### 保留的旧 API（向后兼容）

| 函数 | 说明 |
|------|------|
| `process_all_cards_v2_legacy(rank_dir, suit_dir)` | 旧方案批量处理 |
| `match_card_rank(image_path, template_dir)` | 单张卡片点数匹配 |
| `match_card_suit(image_path, template_dir)` | 单张卡片花色匹配 |
| `TemplateManager(template_dir)` | 旧点数模板管理器 |
| `SuitTemplateManager(template_dir)` | 旧花色模板管理器 |

---

## 模板创建流程

### 使用 AI 自动标注

```python
# 1. 分割卡片
splitter = CardSplitter()
splitter.split_cards(image)

# 2. 裁切信息区域
for filename in os.listdir('Single_Card_Images'):
    img = cv2.imread(filename)
    h, w = img.shape[:2]
    region = img[0:h, 0:int(w*0.25)]
    cv2.imwrite(f'Card_Info_Temp/{filename}', binarize(region))

# 3. AI 识别标注
# 使用 look_at 工具识别每张牌的点数和花色

# 4. 创建模板
for src_name, label in card_labels.items():
    shutil.copy(f'Card_Info_Temp/{src_name}', f'Card_Info_Templates/set_1/{label}.png')
```

---

## 性能对比

| 指标 | 旧方案 | 新方案 | 变化 |
|------|--------|--------|------|
| 模板数量 | 104 (52+52) | 52 | -50% |
| 中间目录 | 2 (Rank+Suit) | 0 | -100% |
| 中间文件 | 104/牌组 | 0 | -100% |
| 提取步骤 | 2次 | 1次 | -50% |
| 颜色检测 | 需要 | 不需要 | 移除 |
| 匹配耗时 (1080p) | 442ms | 1058ms | +140% |
| 代码行数 | ~500行 | ~200行 | -60% |

注: 匹配耗时增加是因为整体匹配需要检查所有52个模板，而旧方案通过颜色过滤只需检查26个。可通过优化匹配算法（如颜色预过滤）改善。

---

## 文件结构

```
Freecell_Card_Match/
├── extract_numbers.py           # 提取模块（新增整体裁切）
├── match_numbers.py             # 匹配模块（新增整体匹配器）
├── Card_Info_Templates/         # 整体模板目录（新增）
│   ├── set_1920x1080/           #   1080p 模板集
│   │   ├── AH.png               #     红桃A
│   │   ├── 2S.png               #     黑桃2
│   │   └── ...
│   └── set_2880x1800/           #   1800p 模板集
├── Card_Rank_Templates/         # 旧点数模板（保留向后兼容）
├── Card_Suit_Templates/         # 旧花色模板（保留向后兼容）
└── Single_Card_Images/          # 分割后的单张纸牌
```

---

## 迁移指南

### 从旧方案迁移到新方案

1. **创建整体模板**
   - 使用 AI 自动标注流程创建 `Card_Info_Templates/` 下的模板

2. **更新调用代码**
   ```python
   # 旧方案
   extract_numbers.process_cards_legacy()
   results, _ = match_numbers.process_all_cards_v2_legacy(rank_dir, suit_dir)
   
   # 新方案
   results, _ = match_numbers.process_all_cards_combined('Card_Info_Templates/set_1920x1080')
   ```

3. **删除旧模板（可选）**
   - 确认新方案工作正常后，可删除 `Card_Rank_Templates/` 和 `Card_Suit_Templates/`

---

## 后续优化方向

1. **匹配性能优化**
   - 颜色预过滤：先检测红/黑，只匹配对应颜色的模板（26个而非52个）
   - 尺寸预筛选：根据卡片尺寸选择对应分辨率的模板集

2. **多分辨率支持**
   - 为 1800p 创建独立的整体模板集
   - 自动检测卡片尺寸选择模板集

3. **模板质量提升**
   - 使用更多样本创建模板（每种牌多个变体）
   - 支持模板自动更新（学习机制）
