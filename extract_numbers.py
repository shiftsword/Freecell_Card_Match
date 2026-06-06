"""
FreeCell纸牌信息提取模块 (v3.0 - 整体裁切)

裁切卡片左上角信息区域（点数+花色），输出到单一目录。
匹配时从整体图像中分割点数和花色分别匹配。
"""

import cv2
import numpy as np
import os


def _detect_color(img):
    """检测卡片颜色类型（红/黑）"""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, w = img.shape[:2]
    roi = hsv[0:int(h*0.5), 0:int(w*0.25)]
    
    red1 = cv2.inRange(roi, np.array([0, 100, 100]), np.array([10, 255, 255]))
    red2 = cv2.inRange(roi, np.array([170, 100, 100]), np.array([180, 255, 255]))
    red_mask = red1 + red2
    glow = cv2.inRange(roi, np.array([15, 50, 150]), np.array([35, 255, 255]))
    red_mask = cv2.bitwise_and(red_mask, cv2.bitwise_not(glow))
    black_mask = cv2.inRange(roi, np.array([0, 0, 0]), np.array([180, 255, 50]))
    return '_r' if cv2.countNonZero(red_mask) > cv2.countNonZero(black_mask) else '_b'


def _binarize(region):
    """转为白底黑字二值图"""
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)
    kernel = np.ones((2, 2), np.uint8)
    binary = cv2.dilate(binary, kernel, iterations=1)
    binary = cv2.erode(binary, kernel, iterations=1)
    output = cv2.bitwise_not(binary)
    output[output < 128] = 0
    output[output >= 128] = 255
    return output


def extract_info_region(image_path):
    """裁切卡片左上角信息区域（点数+花色整体）。
    返回: (info_img, color_type) 或 None
    """
    img = cv2.imread(image_path)
    if img is None:
        return None
    h, w = img.shape[:2]
    color_type = _detect_color(img)
    crop_w = int(w * 0.25)
    region = img[0:h, 0:crop_w]
    return _binarize(region), color_type


def process_cards():
    """处理所有卡片，提取信息区域到 Card_Info_Images（匹配用）"""
    output_dir = 'Card_Info_Images'
    os.makedirs(output_dir, exist_ok=True)
    
    cards_dir = 'Single_Card_Images'
    if not os.path.exists(cards_dir):
        return
    
    for filename in os.listdir(cards_dir):
        if not filename.endswith('.png'):
            continue
        image_path = os.path.join(cards_dir, filename)
        result = extract_info_region(image_path)
        if result is None:
            continue
        info_img, color_type = result
        name, ext = os.path.splitext(filename)
        output_path = os.path.join(output_dir, f'{name}{color_type}{ext}')
        cv2.imwrite(output_path, info_img)


# ============================================================
# 旧版提取（供模板创建工具使用）
# ============================================================

def _extract_number_legacy(image_path, padding=2):
    img = cv2.imread(image_path)
    if img is None:
        return None
    
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    height, width = img.shape[:2]
    roi_height = int(height/1.5)
    roi_width = int(width/4)
    roi = hsv[0:roi_height, 0:roi_width]
    
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    red_mask1 = cv2.inRange(roi, lower_red1, upper_red1)
    red_mask2 = cv2.inRange(roi, lower_red2, upper_red2)
    red_mask = red_mask1 + red_mask2

    lower_glow = np.array([15, 50, 150])
    upper_glow = np.array([35, 255, 255])
    glow_mask = cv2.inRange(roi, lower_glow, upper_glow)
    red_mask = cv2.bitwise_and(red_mask, cv2.bitwise_not(glow_mask))

    lower_black = np.array([0, 0, 0])
    upper_black = np.array([180, 255, 50])
    black_mask = cv2.inRange(roi, lower_black, upper_black)

    red_pixels = cv2.countNonZero(red_mask)
    black_pixels = cv2.countNonZero(black_mask)
    color_type = '_r' if red_pixels > black_pixels else '_b'

    combined_mask = cv2.bitwise_or(red_mask, black_mask)
    combined_mask = cv2.bitwise_and(combined_mask, cv2.bitwise_not(glow_mask))
    
    contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
        
    max_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(max_contour)
    
    search_region = combined_mask[y:y+h, max(0, x-20):x]
    left_contours, _ = cv2.findContours(search_region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if left_contours:
        left_x = x - 15 + min([cv2.boundingRect(c)[0] for c in left_contours])
        x_start = max(0, left_x - padding)
    else:
        x_start = max(0, x - padding)
        
    x_end = min(roi_width, x + w + padding)
    y_start = max(0, y - padding)
    y_end = min(roi_height, y + h + padding)
    
    number_region = combined_mask[y_start:y_end, x_start:x_end]
    padded_region = np.zeros((y_end - y_start, x_end - x_start), dtype=np.uint8)
    padded_region[0:number_region.shape[0], 0:number_region.shape[1]] = number_region
    
    kernel = np.ones((2,2), np.uint8)
    padded_region = cv2.dilate(padded_region, kernel, iterations=1)
    padded_region = cv2.erode(padded_region, kernel, iterations=1)
    
    output = cv2.bitwise_not(padded_region)
    output[output < 128] = 0
    output[output >= 128] = 255
    
    suit_output = _extract_suit_legacy(img, color_type)
    return output, suit_output, color_type


def _extract_suit_legacy(img, color_type):
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    height, width = img.shape[:2]
    
    lower_glow = np.array([15, 50, 150])
    upper_glow = np.array([35, 255, 255])
    glow_mask = cv2.inRange(hsv, lower_glow, upper_glow)
    
    if color_type == '_r':
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 100, 100])
        upper_red2 = np.array([180, 255, 255])
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        color_mask = mask1 + mask2
        color_mask = cv2.bitwise_and(color_mask, cv2.bitwise_not(glow_mask))
    else:
        lower_black = np.array([0, 0, 0])
        upper_black = np.array([180, 255, 50])
        color_mask = cv2.inRange(hsv, lower_black, upper_black)
    
    all_mask = cv2.bitwise_or(color_mask, cv2.inRange(hsv, np.array([0,0,0]), np.array([180,255,50])))
    all_mask = cv2.bitwise_and(all_mask, cv2.bitwise_not(glow_mask))
    
    scale = height / 58.0
    rank_y_limit = int(height * 0.26)
    rank_x_limit = int(width * 0.17)
    min_area = int(30 * scale * scale)
    default_rank_bottom = int(height * 0.47)
    search_height = int(height * 0.38)
    search_x_max = int(width * 0.20)

    contours, _ = cv2.findContours(all_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    rank_bottom = 0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > min_area:
            x, y, cw, ch = cv2.boundingRect(cnt)
            if y < rank_y_limit and x < rank_x_limit:
                rank_bottom = max(rank_bottom, y + ch)
    if rank_bottom == 0:
        rank_bottom = default_rank_bottom
    
    search_start = rank_bottom + int(2 * scale)
    search_end = min(height, rank_bottom + search_height)
    suit_region = all_mask[search_start:search_end, 0:search_x_max]
    
    points = cv2.findNonZero(suit_region)
    if points is None or len(points) < 5:
        suit_output = np.zeros((10, 10), dtype=np.uint8)
        suit_output[:] = 255
        return suit_output
    
    x, y, cw, ch = cv2.boundingRect(points)
    padding = 2
    y1 = max(0, y + search_start - padding)
    y2 = min(height, y + search_start + ch + padding)
    x1 = max(0, x - padding)
    x2 = min(search_x_max, x + cw + padding)
    
    suit_crop = all_mask[y1:y2, x1:x2]
    suit_output = cv2.bitwise_not(suit_crop)
    suit_output[suit_output < 128] = 0
    suit_output[suit_output >= 128] = 255
    return suit_output


def process_cards_legacy():
    """旧版提取：分别输出到 Card_Rank_Images 和 Card_Suit_Images（模板创建用）"""
    output_dir = 'Card_Rank_Images'
    suit_output_dir = 'Card_Suit_Images'
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(suit_output_dir, exist_ok=True)
    
    cards_dir = 'Single_Card_Images'
    if not os.path.exists(cards_dir):
        return
    
    for filename in os.listdir(cards_dir):
        if not filename.endswith('.png'):
            continue
        image_path = os.path.join(cards_dir, filename)
        result = _extract_number_legacy(image_path)
        if result is None:
            continue
        number_img, suit_img, color_type = result
        name, ext = os.path.splitext(filename)
        cv2.imwrite(os.path.join(output_dir, f'{name}{color_type}{ext}'), number_img)
        cv2.imwrite(os.path.join(suit_output_dir, f'{name}{color_type}{ext}'), suit_img)


if __name__ == "__main__":
    process_cards()
