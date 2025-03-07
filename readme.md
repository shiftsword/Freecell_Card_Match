# FreeCell OCR 纸牌识别工具

一个专门用于识别FreeCell(空当接龙)游戏截图并生成标准布局的工具。

## 项目概述

本项目通过计算机视觉和OCR技术，实现对FreeCell游戏截图的自动分析，提取每张纸牌的数字和花色信息，并生成标准的FreeCell布局格式，方便玩家记录和分享游戏局面。

## 功能特性

- **自动分割**: 从游戏截图中精确分割出52张纸牌
- **数字识别**: 使用优化的OCR技术识别纸牌数字(A,2-9,10,J,Q,K)
- **花色识别**: 通过颜色分析区分红色(红心♥和方块♦)和黑色(黑桃♠和梅花♣)
- **布局生成**: 输出标准的FreeCell布局格式
- **完整性验证**: 自动检查牌组是否完整合法

## 技术实现

### 处理流程

1. **图像分割**: 将游戏截图分割为8列，然后提取每列中的单张纸牌
2. **数字提取**: 从每张纸牌中提取左上角的数字区域
3. **OCR识别**: 使用Tesseract OCR引擎识别数字
4. **布局格式化**: 将识别结果转换为标准FreeCell布局格式

### 核心模块

- `card_splitter.py`: 纸牌图像裁切模块
- `extract_numbers.py`: 纸牌数字提取模块
- `recognize_numbers.py`: 纸牌数字识别模块

## 使用方法

### 环境要求

- Python 3.6+
- OpenCV
- NumPy
- Pytesseract (需要安装Tesseract OCR引擎)

### 安装依赖

```bash
pip install opencv-python numpy pytesseract
```

### 使用步骤

1. 准备FreeCell游戏截图，命名为`test.png`并放在项目根目录
2. 运行图像分割:

```bash
python test_splitter.py
```

3. 提取数字区域:

```bash
python extract_numbers.py
```

4. 识别数字并生成布局:

```bash
python recognize_numbers.py
```

5. 查看结果:
   - 识别日志: `ocr-result.log`
   - 最终布局: 日志文件末尾的FreeCell布局格式

### 输出示例

```
# MS Freecell Game Layout
#
: 8S 8C KH 7S JH 7H 5H
: 4S 3H JD 8H AH 4H 3S
: TH QS 6S AS 9H 2H AD
: 9S 7C TS QH TD 6H QD
: 5S KS JS 6D 2S QC
: 9C 9D 2D 4C AC KC
: 3C 3D 2C 4D 8D 6C
: 5D JC 7D TC 5C KD

# 牌组完整且合法
```

## 性能指标

- 识别准确率: >99% (在标准分辨率截图上)
- 处理速度: 约30-40秒处理完整局面(52张牌)
- 单卡识别时间: 600-900ms/张

## 优化技巧

- 使用HSV色彩空间进行图像预处理
- 应用CLAHE算法增强对比度
- 多模式OCR识别提高准确率
- 自适应阈值优化二值化效果

## 常见问题

1. **识别失败**: 检查截图质量，确保分辨率足够高且边缘清晰
2. **花色错误**: 系统通过红黑色区分花色，可能需要调整HSV阈值
3. **布局验证失败**: 检查是否有重复或缺失的牌

## 项目结构

```
FreeCell_OCR/
├── card_splitter.py    # 纸牌图像裁切模块
├── extract_numbers.py  # 纸牌数字提取模块
├── recognize_numbers.py # 纸牌数字识别模块
├── test_splitter.py    # 分割测试脚本
├── deepseek.md         # 技术方案文档
├── test.png            # 测试用游戏截图
├── cards/              # 分割后的纸牌图像
├── output/             # 提取的数字图像
└── ocr-result.log      # 识别结果日志
```

## 许可证

[MIT License](https://opensource.org/licenses/MIT)

## 致谢

- Tesseract OCR引擎
- OpenCV计算机视觉库
```
