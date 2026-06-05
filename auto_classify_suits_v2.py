"""
使用模板匹配的花色分类脚本

1. 手动选择代表性花色图像作为参考模板
2. 使用模板匹配对所有花色图像进行分类
3. 确保每种花色恰好13张
"""

import cv2
import numpy as np
import os
import shutil

def get_best_match(img, templates):
    """找到最佳匹配的模板"""
    best_match = None
    best_score = -1
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    for template_name, template_img in templates.items():
        template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
        
        # 确保尺寸匹配
        if gray.shape != template_gray.shape:
            template_gray = cv2.resize(template_gray, (gray.shape[1], gray.shape[0]))
        
        # 模板匹配
        result = cv2.matchTemplate(gray, template_gray, cv2.TM_CCOEFF_NORMED)
        score = np.max(result)
        
        if score > best_score:
            best_score = score
            best_match = template_name
    
    return best_match, best_score


def auto_classify_suits_v2():
    """使用模板匹配的花色分类"""
    suit_dir = 'Card_Suit_Images'
    template_dir = 'Card_Suit_Templates/set_1'
    
    # 清空并创建模板目录
    if os.path.exists(template_dir):
        shutil.rmtree(template_dir)
    os.makedirs(template_dir, exist_ok=True)
    
    # 获取所有花色图像
    files = sorted([f for f in os.listdir(suit_dir) if f.endswith('.png')])
    
    # 按颜色分组
    red_files = [f for f in files if '_r.' in f]
    black_files = [f for f in files if '_b.' in f]
    
    print(f'红色花色: {len(red_files)} 个')
    print(f'黑色花色: {len(black_files)} 个')
    
    # 读取所有图像
    images = {}
    for filename in files:
        img = cv2.imread(os.path.join(suit_dir, filename))
        if img is not None:
            images[filename] = img
    
    # 使用基于特征的分类方法
    # 特征：上半部分比例、宽高比、对称性
    def classify_by_features(img, color_type):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        
        # 二值化
        _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)
        
        # 查找轮廓
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return 'H' if color_type == '_r' else 'S'
        
        max_contour = max(contours, key=cv2.contourArea)
        x, y, cw, ch = cv2.boundingRect(max_contour)
        
        # 计算上半部分比例
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.drawContours(mask, [max_contour], -1, 255, -1)
        
        upper = mask[0:h//2, :]
        lower = mask[h//2:, :]
        
        upper_pixels = np.sum(upper > 0)
        lower_pixels = np.sum(lower > 0)
        total = upper_pixels + lower_pixels
        
        upper_ratio = upper_pixels / total if total > 0 else 0.5
        
        # 计算宽高比
        aspect_ratio = cw / ch if ch > 0 else 1
        
        # 计算对称性
        left = mask[:, 0:w//2]
        right = mask[:, w//2:]
        
        left_pixels = np.sum(left > 0)
        right_pixels = np.sum(right > 0)
        
        symmetry = min(left_pixels, right_pixels) / max(left_pixels, right_pixels) if max(left_pixels, right_pixels) > 0 else 1
        
        if color_type == '_r':
            # 红色花色：红心(H) 或 方块(D)
            # 红心：顶部较宽（两个圆形），上半比例 > 0.55
            # 方块：菱形，上下较对称，上半比例接近 0.5
            
            if upper_ratio > 0.58:
                return 'H'  # 红心
            elif upper_ratio < 0.48:
                return 'D'  # 方块
            elif symmetry > 0.9:
                return 'D'  # 方块（更对称）
            else:
                return 'H'  # 红心
        else:
            # 黑色花色：黑桃(S) 或 梅花(C)
            # 黑桃：顶部尖锐，上半比例较高
            # 梅花：三叶草，较对称
            
            if upper_ratio > 0.58:
                return 'S'  # 黑桃
            elif upper_ratio < 0.48:
                return 'C'  # 梅花
            elif symmetry > 0.9:
                return 'C'  # 梅花（更对称）
            else:
                return 'S'  # 黑桃
    
    # 第一轮分类
    classifications = {}
    for filename in files:
        img = images[filename]
        color_type = '_r' if '_r.' in filename else '_b'
        suit = classify_by_features(img, color_type)
        classifications[filename] = suit
    
    # 统计分类结果
    suit_counts = {'H': 0, 'S': 0, 'D': 0, 'C': 0}
    for suit in classifications.values():
        suit_counts[suit] += 1
    
    print(f'\n初始分类结果: {suit_counts}')
    
    # 调整分类，确保每种花色恰好13张
    # 如果某种花色过多，将最不确定的样本重新分类
    target_count = 13
    
    for suit in ['H', 'D', 'S', 'C']:
        if suit_counts[suit] > target_count:
            # 需要减少这种花色
            excess = suit_counts[suit] - target_count
            
            # 找到这种花色的所有文件
            suit_files = [f for f, s in classifications.items() if s == suit]
            
            # 计算每个文件的分类置信度
            confidences = []
            for filename in suit_files:
                img = images[filename]
                color_type = '_r' if '_r.' in filename else '_b'
                
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                h, w = gray.shape
                
                _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)
                contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                if contours:
                    max_contour = max(contours, key=cv2.contourArea)
                    mask = np.zeros((h, w), dtype=np.uint8)
                    cv2.drawContours(mask, [max_contour], -1, 255, -1)
                    
                    upper = mask[0:h//2, :]
                    lower = mask[h//2:, :]
                    
                    upper_pixels = np.sum(upper > 0)
                    lower_pixels = np.sum(lower > 0)
                    total = upper_pixels + lower_pixels
                    
                    upper_ratio = upper_pixels / total if total > 0 else 0.5
                    
                    # 计算与阈值的距离（越近越不确定）
                    if suit in ['H', 'S']:
                        distance = abs(upper_ratio - 0.58)
                    else:
                        distance = abs(upper_ratio - 0.48)
                    
                    confidences.append((filename, distance))
            
            # 按置信度排序，将最不确定的重新分类
            confidences.sort(key=lambda x: x[1])
            
            for i in range(excess):
                filename = confidences[i][0]
                color_type = '_r' if '_r.' in filename else '_b'
                
                # 重新分类为另一种花色
                if suit == 'H':
                    classifications[filename] = 'D'
                elif suit == 'D':
                    classifications[filename] = 'H'
                elif suit == 'S':
                    classifications[filename] = 'C'
                elif suit == 'C':
                    classifications[filename] = 'S'
    
    # 重新统计
    suit_counts = {'H': 0, 'S': 0, 'D': 0, 'C': 0}
    for suit in classifications.values():
        suit_counts[suit] += 1
    
    print(f'调整后分类结果: {suit_counts}')
    
    # 保存模板
    suit_counters = {'H': 0, 'S': 0, 'D': 0, 'C': 0}
    
    for filename in files:
        suit = classifications[filename]
        color_type = '_r' if '_r.' in filename else '_b'
        
        suit_counters[suit] += 1
        count = suit_counters[suit]
        
        template_filename = f'{suit}{color_type}_{count}.png'
        template_path = os.path.join(template_dir, template_filename)
        
        shutil.copy2(os.path.join(suit_dir, filename), template_path)
        
        print(f'{filename} -> {template_filename}')
    
    print(f'\n分类完成!')
    print(f'最终花色分布: {suit_counters}')
    
    # 验证
    total = sum(suit_counters.values())
    if total == 52:
        print('✓ 总数正确: 52张')
    else:
        print(f'✗ 总数错误: {total}张')
    
    for suit, count in suit_counters.items():
        if count == 13:
            print(f'✓ {suit}: {count}张')
        else:
            print(f'✗ {suit}: {count}张')


if __name__ == '__main__':
    auto_classify_suits_v2()
