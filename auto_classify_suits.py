"""
自动花色分类脚本

通过分析花色图像的形状特征，自动将花色分类为：
- H (红心 Hearts)
- S (黑桃 Spades)
- D (方块 Diamonds)
- C (梅花 Clubs)
"""

import cv2
import numpy as np
import os
import shutil

def analyze_suit_shape(img):
    """分析花色图像的形状特征"""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    
    # 二值化
    _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)
    
    # 查找轮廓
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None, 0
    
    # 找到最大轮廓
    max_contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(max_contour)
    
    if area < 20:
        return None, 0
    
    # 计算边界矩矩
    x, y, cw, ch = cv2.boundingRect(max_contour)
    
    # 计算轮廓的矩
    moments = cv2.moments(max_contour)
    if moments['m00'] == 0:
        return None, 0
    
    # 重心
    cx = moments['m10'] / moments['m00']
    cy = moments['m01'] / moments['m00']
    
    # 计算形状特征
    # 1. 宽高比
    aspect_ratio = cw / ch if ch > 0 else 1
    
    # 2. 轮廓面积与边界矩形面积的比值（填充度）
    rect_area = cw * ch
    extent = area / rect_area if rect_area > 0 else 0
    
    # 3. 轮廓面积与凸包面积的比值（凸度）
    hull = cv2.convexHull(max_contour)
    hull_area = cv2.contourArea(hull)
    solidity = area / hull_area if hull_area > 0 else 0
    
    # 4. 计算上半部分和下半部分的黑色像素比例
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.drawContours(mask, [max_contour], -1, 255, -1)
    
    upper_half = mask[0:h//2, :]
    lower_half = mask[h//2:, :]
    
    upper_pixels = np.sum(upper_half > 0)
    lower_pixels = np.sum(lower_half > 0)
    total_pixels = upper_pixels + lower_pixels
    
    upper_ratio = upper_pixels / total_pixels if total_pixels > 0 else 0.5
    
    # 5. 计算左右对称性
    left_half = mask[:, 0:w//2]
    right_half = mask[:, w//2:]
    
    left_pixels = np.sum(left_half > 0)
    right_pixels = np.sum(right_half > 0)
    
    symmetry = min(left_pixels, right_pixels) / max(left_pixels, right_pixels) if max(left_pixels, right_pixels) > 0 else 1
    
    return {
        'area': area,
        'aspect_ratio': aspect_ratio,
        'extent': extent,
        'solidity': solidity,
        'upper_ratio': upper_ratio,
        'symmetry': symmetry,
        'cx': cx,
        'cy': cy,
        'cw': cw,
        'ch': ch
    }, area


def classify_suit(features, color_type):
    """根据特征分类花色"""
    if features is None:
        return 'H' if color_type == '_r' else 'S'
    
    aspect_ratio = features['aspect_ratio']
    upper_ratio = features['upper_ratio']
    solidity = features['solidity']
    symmetry = features['symmetry']
    
    if color_type == '_r':
        # 红色花色：红心(H) 或 方块(D)
        # 红心特征：顶部较宽（两个圆形），底部尖，上半部分比例较高
        # 方块特征：菱形，上下对称，宽高比接近1
        
        if upper_ratio > 0.55 and aspect_ratio < 1.2:
            return 'H'  # 红心
        elif aspect_ratio > 0.8 and aspect_ratio < 1.2 and abs(upper_ratio - 0.5) < 0.1:
            return 'D'  # 方块
        elif upper_ratio > 0.5:
            return 'H'  # 红心
        else:
            return 'D'  # 方块
    else:
        # 黑色花色：黑桃(S) 或 梅花(C)
        # 黑桃特征：顶部尖锐，底部圆形，上半部分比例较高
        # 梅花特征：三叶草形状，三个圆形凸起，较对称
        
        if upper_ratio > 0.55 and aspect_ratio < 1.0:
            return 'S'  # 黑桃
        elif symmetry > 0.85 and aspect_ratio > 0.8:
            return 'C'  # 梅花
        elif upper_ratio > 0.5:
            return 'S'  # 黑桃
        else:
            return 'C'  # 梅花


def auto_classify_suits():
    """自动分类所有花色图像"""
    suit_dir = 'Card_Suit_Images'
    template_dir = 'Card_Suit_Templates/set_1'
    
    # 创建模板目录
    os.makedirs(template_dir, exist_ok=True)
    
    # 获取所有花色图像
    files = sorted([f for f in os.listdir(suit_dir) if f.endswith('.png')])
    
    print(f'共有 {len(files)} 个花色图像需要分类')
    
    # 统计每种花色的数量
    suit_counts = {'H': 0, 'S': 0, 'D': 0, 'C': 0}
    
    for filename in files:
        img_path = os.path.join(suit_dir, filename)
        img = cv2.imread(img_path)
        
        if img is None:
            print(f'无法读取: {filename}')
            continue
        
        # 分析形状特征
        features, area = analyze_suit_shape(img)
        
        # 获取颜色类型
        color_type = '_r' if '_r.' in filename else '_b'
        
        # 分类花色
        suit = classify_suit(features, color_type)
        
        # 更新计数
        suit_counts[suit] += 1
        count = suit_counts[suit]
        
        # 生成模板文件名
        template_filename = f'{suit}{color_type}_{count}.png'
        template_path = os.path.join(template_dir, template_filename)
        
        # 复制图像到模板目录
        shutil.copy2(img_path, template_path)
        
        print(f'{filename} -> {template_filename} ({suit})')
    
    print(f'\n分类完成!')
    print(f'花色分布: {suit_counts}')
    
    # 验证分类结果
    total = sum(suit_counts.values())
    if total == 52:
        print('✓ 总数正确: 52张')
    else:
        print(f'✗ 总数错误: {total}张 (应为52张)')
    
    for suit, count in suit_counts.items():
        if count == 13:
            print(f'✓ {suit}: {count}张')
        else:
            print(f'✗ {suit}: {count}张 (应为13张)')


if __name__ == '__main__':
    auto_classify_suits()
