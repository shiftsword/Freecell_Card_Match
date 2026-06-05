"""测试 Freecell_Layout_2.png"""
import os
import cv2
import time
import numpy as np
from card_splitter import CardSplitter
import extract_numbers
import match_numbers

image_path = "Freecell_Layout_2.png"
print(f"测试图片: {image_path}")
print("="*60)

# 清理工作目录
for d in ["Single_Card_Images", "Card_Rank_Images"]:
    if os.path.exists(d):
        for f in os.listdir(d):
            os.remove(os.path.join(d, f))
    os.makedirs(d, exist_ok=True)

start_time = time.time()

# 步骤1: 分割纸牌
print("\n[步骤1/3] 分割纸牌...")
image = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
print(f"图像尺寸: {image.shape[1]}x{image.shape[0]}")
splitter = CardSplitter()
splitter.split_cards(image)
print("纸牌分割完成")

# 步骤2: 提取数字
print("\n[步骤2/3] 提取数字...")
extract_numbers.process_cards()
print("数字提取完成")

# 步骤3: 识别
print("\n[步骤3/3] 识别数字并生成布局...")
card_dir = "Single_Card_Images"
card_files = [f for f in os.listdir(card_dir) if f.endswith('.png')]
template_set = "set_1"
if card_files:
    first_card = os.path.join(card_dir, card_files[0])
    img = cv2.imread(first_card)
    if img is not None:
        h, w = img.shape[:2]
        print(f"单张纸牌尺寸: {w}x{h}")
        if w >= 200 or h >= 80:
            template_set = "set_2880x1800"
        else:
            template_set = "set_1920x1080"

template_dir = os.path.join('Card_Rank_Templates', template_set)
print(f"使用模板集: {template_set}")

results = []
input_dir = 'Card_Rank_Images'
image_files = sorted([f for f in os.listdir(input_dir) if f.endswith('.png')])
success_count = 0
fail_count = 0

for filename in image_files:
    fpath = os.path.join(input_dir, filename)
    number, confidence, match_count, process_time = match_numbers.match_card_rank(fpath, template_dir)
    color_simple = 'r' if '_r.' in filename else 'b'
    if number:
        results.append({'number': number, 'color': color_simple, 'filename': filename})
        success_count += 1
    else:
        results.append({'number': '?', 'color': color_simple, 'filename': filename})
        fail_count += 1

if results:
    columns, _, _ = match_numbers.results_to_columns(results)
    layout_lines, is_valid, errors = match_numbers.format_columns_to_text(columns)

    print("\n识别结果布局:")
    print("-" * 40)
    for line in layout_lines:
        print(line)
    print("-" * 40)

    total_time = int((time.time() - start_time) * 1000)
    print(f"\n统计信息:")
    print(f"  成功识别: {success_count} 张")
    print(f"  识别失败: {fail_count} 张")
    print(f"  总用时: {total_time}ms")
    print(f"  布局验证: {'通过' if is_valid else '未通过'}")
    if not is_valid:
        print("  验证错误:")
        for error in errors:
            print(f"    - {error}")
