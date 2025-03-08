"""
FreeCell纸牌数字提取模块

图像特征:
- 纸牌左上角包含数字和花色信息
- 红色(红心♥和方块♦)和黑色(黑桃♠和梅花♣)两种颜色
- 数字可能是单个字符(A,2-9,J,Q,K)或双字符(10)
- 花色标志紧邻数字

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

3. 图像优化
   - 应用形态学操作(膨胀和腐蚀)增强数字清晰度
   - 转换为白底黑字格式，便于OCR识别
   - 使用原始文件名加颜色标识(_r或_b)保存结果
"""

import cv2
import numpy as np
import os

def extract_number(image_path, padding=2):
    # 读取图片
    img = cv2.imread(image_path)
    if img is None:
        print(f"无法读取图片: {image_path}")
        return None
    
    # 转换到HSV颜色空间，便于处理红黑两色
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # 提取左上角区域进行分析
    height, width = img.shape[:2]
    roi_height = int(height/1.5)
    roi_width = int(width/4)
    roi = hsv[0:roi_height, 0:roi_width]
    
    # 分析ROI区域内的颜色分布
    h, s, v = cv2.split(roi)
    
    # 创建掩码，分别处理红色和黑色数字
    # 红色掩码（处理红心和方块）
    lower_red1 = np.array([0, 100, 100])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 100, 100])
    upper_red2 = np.array([180, 255, 255])
    red_mask1 = cv2.inRange(roi, lower_red1, upper_red1)
    red_mask2 = cv2.inRange(roi, lower_red2, upper_red2)
    red_mask = red_mask1 + red_mask2
    
    # 黑色掩码（处理黑桃和梅花）
    lower_black = np.array([0, 0, 0])
    upper_black = np.array([180, 255, 50])
    black_mask = cv2.inRange(roi, lower_black, upper_black)
    
    # 确定颜色类型
    red_pixels = cv2.countNonZero(red_mask)
    black_pixels = cv2.countNonZero(black_mask)
    color_type = '_r' if red_pixels > black_pixels else '_b'
    
    # 合并掩码
    combined_mask = cv2.bitwise_or(red_mask, black_mask)
    
    # 寻找连通区域
    contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return None
        
    # 找到最大的连通区域（通常是数字）
    max_contour = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(max_contour)
    
    # 在原始位置左侧搜索可能的相连数字
    search_region = combined_mask[y:y+h, max(0, x-20):x]  # 向左搜索20像素
    left_contours, _ = cv2.findContours(search_region, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if left_contours:
        # 如果左侧有数字，扩展提取区域
        left_x = x - 15 + min([cv2.boundingRect(c)[0] for c in left_contours])
        x_start = max(0, left_x - padding)  # 使用参数化的padding值
    else:
        x_start = max(0, x - padding)  # 使用参数化的padding值
        
    # 设置其他边界，同样使用参数化的padding值
    x_end = min(roi_width, x + w + padding)
    y_start = max(0, y - padding)
    y_end = min(roi_height, y + h + padding)
    
    # 提取数字区域
    number_region = combined_mask[y_start:y_end, x_start:x_end]
    
    # 创建带padding的空白图像
    padded_region = np.zeros((y_end - y_start, x_end - x_start), dtype=np.uint8)
    padded_region[:] = 0  # 设置背景为黑色
    
    # 将数字区域复制到带padding的图像中
    padded_region[0:number_region.shape[0], 0:number_region.shape[1]] = number_region
    
    # 对提取区域进行处理
    kernel = np.ones((2,2), np.uint8)
    padded_region = cv2.dilate(padded_region, kernel, iterations=1)
    padded_region = cv2.erode(padded_region, kernel, iterations=1)
    
    # 创建白底黑字的输出图像
    output = cv2.bitwise_not(padded_region)
    
    # 填充背景为白色
    output[output < 128] = 0
    output[output >= 128] = 255
    
    return output, color_type

def process_cards(padding=2):
    # 创建输出目录
    output_dir = 'Card_Rank_Images'
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取cards目录中的所有png文件
    cards_dir = 'Single_Card_Images'
    if not os.path.exists(cards_dir):
        print(f"Single_Card_Images目录不存在")
        return
        
    image_files = [f for f in os.listdir(cards_dir) if f.endswith('.png')]
    
    for filename in image_files:
        image_path = os.path.join(cards_dir, filename)
        result = extract_number(image_path, padding)
        if result is None:
            continue
            
        number_img, color_type = result
        
        # 在文件名中添加颜色标识
        name, ext = os.path.splitext(filename)
        output_path = os.path.join(output_dir, f'{name}{color_type}{ext}')
        cv2.imwrite(output_path, number_img)
        print(f"处理完成: {output_path}")

# 只有在直接运行此脚本时才执行process_cards()
if __name__ == "__main__":
    process_cards()