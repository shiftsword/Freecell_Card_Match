"""
FreeCell纸牌数字和花色提取模块

图像特征:
- 纸牌左上角包含数字和花色信息
- 红色(红心♥和方块♦)和黑色(黑桃♠和梅花♣)两种颜色
- 数字可能是单个字符(A,2-9,J,Q,K)或双字符(10)
- 花色符号在数字正下方

实现方法:
1. 颜色识别
   - 将图像转换为HSV颜色空间
   - 提取左上角区域作为ROI
   - 使用红色范围([0,100,100]-[10,255,255]和[170,100,100]-[180,255,255])创建红色掩码
   - 使用黑色范围([0,0,0]-[180,255,50])创建黑色掩码
   - 通过像素计数确定纸牌颜色类型

2. 数字定位
   - 合并红黑掩码
   - 使用轮廓检测找到最大连通区域(通常是数字)
   - 向左搜索可能的相连数字(处理10这种双字符)
   - 添加适当的padding确保完整捕获数字

3. 花色定位
   - 在数字区域下方寻找花色符号
   - 提取花色符号区域用于模板匹配

4. 图像优化
   - 应用形态学操作(膨胀和腐蚀)增强数字清晰度
   - 转换为白底黑字格式，便于OCR识别
   - 使用原始文件名加颜色标识(_r或_b)保存结果
"""

import cv2
import numpy as np
import os

def extract_number(image_path, padding=2):
    img = cv2.imread(image_path)
    if img is None:
        return None
    
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    height, width = img.shape[:2]
    roi_height = int(height/1.5)
    roi_width = int(width/4)
    roi = hsv[0:roi_height, 0:roi_width]
    
    h, s, v = cv2.split(roi)

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
    padded_region[:] = 0
    
    padded_region[0:number_region.shape[0], 0:number_region.shape[1]] = number_region
    
    kernel = np.ones((2,2), np.uint8)
    padded_region = cv2.dilate(padded_region, kernel, iterations=1)
    padded_region = cv2.erode(padded_region, kernel, iterations=1)
    
    output = cv2.bitwise_not(padded_region)
    
    output[output < 128] = 0
    output[output >= 128] = 255
    
    suit_output = extract_suit_from_image(img, color_type)
    
    return output, suit_output, color_type


def extract_suit_from_image(img, color_type):
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
    
    search_y_start = int(height * 0.4)
    search_region = color_mask[search_y_start:height, 0:width]
    
    contours, _ = cv2.findContours(search_region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        suit_output = np.zeros((10, 10), dtype=np.uint8)
        suit_output[:] = 255
        return suit_output
    
    valid_contours = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 20:
            valid_contours.append(cnt)
    
    if not valid_contours:
        suit_output = np.zeros((10, 10), dtype=np.uint8)
        suit_output[:] = 255
        return suit_output
    
    max_contour = max(valid_contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(max_contour)
    y = y + search_y_start
    
    padding = 2
    x_start = max(0, x - padding)
    x_end = min(width, x + w + padding)
    y_start = max(0, y - padding)
    y_end = min(height, y + h + padding)
    
    suit_region = color_mask[y_start:y_end, x_start:x_end]
    
    suit_padded = np.zeros((y_end - y_start, x_end - x_start), dtype=np.uint8)
    suit_padded[:] = 0
    
    if suit_region.shape[0] > 0 and suit_region.shape[1] > 0:
        suit_padded[0:suit_region.shape[0], 0:suit_region.shape[1]] = suit_region
    
    kernel = np.ones((2,2), np.uint8)
    suit_padded = cv2.dilate(suit_padded, kernel, iterations=1)
    suit_padded = cv2.erode(suit_padded, kernel, iterations=1)
    
    suit_output = cv2.bitwise_not(suit_padded)
    suit_output[suit_output < 128] = 0
    suit_output[suit_output >= 128] = 255
    
    return suit_output
    
    return output, suit_output, color_type

def process_cards(padding=2):
    output_dir = 'Card_Rank_Images'
    suit_output_dir = 'Card_Suit_Images'
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(suit_output_dir, exist_ok=True)
    
    cards_dir = 'Single_Card_Images'
    if not os.path.exists(cards_dir):
        return
        
    image_files = [f for f in os.listdir(cards_dir) if f.endswith('.png')]
    
    for filename in image_files:
        image_path = os.path.join(cards_dir, filename)
        result = extract_number(image_path, padding)
        if result is None:
            continue
            
        number_img, suit_img, color_type = result
        
        name, ext = os.path.splitext(filename)
        number_path = os.path.join(output_dir, f'{name}{color_type}{ext}')
        suit_path = os.path.join(suit_output_dir, f'{name}{color_type}{ext}')
        
        cv2.imwrite(number_path, number_img)
        cv2.imwrite(suit_path, suit_img)

if __name__ == "__main__":
    process_cards()