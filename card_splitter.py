"""
FreeCell纸牌图像裁切模块

图像特征:
- 8列7行52张白色纸牌在绿色背景上呈现规则排列
- 前四列是7张纸牌堆叠，后四列是6张纸牌堆叠
- 每列最下方是完整纸牌，上方纸牌只显示一部分，且高度相等
- 图像质量高，边缘清晰

实现方法:
1. 列分割
   - 将图像转换为HSV颜色空间
   - 使用绿色范围([35,30,30] - [85,255,255])创建掩码
   - 应用形态学闭运算去除噪点
   - 通过轮廓检测识别纸牌列
   - 使用面积、高度比等条件过滤有效列

2. 高度计算
   - 获取第一列(7张牌)和第五列(6张牌)的高度
   - 计算高度差得到单张纸牌高度
   - 根据列号确定每列纸牌数量(前4列7张，后4列6张)

3. 单牌分割
   - 从上到下按计算得到的高度裁切
   - 保持原始图像质量不缩放
   - 使用"列号行号.png"格式保存
"""

import cv2
import numpy as np
from typing import List, Tuple
import os

class CardSplitter:
    def __init__(self):
        self.output_dir = "Single_Card_Images"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def _split_columns(self, image: np.ndarray) -> Tuple[List[np.ndarray], List[Tuple[int, int, int, int]]]:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([35, 30, 30]), np.array([85, 255, 255]))
        mask = cv2.bitwise_not(mask)
        
        kernel = np.ones((3,3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        valid_contours = []
        img_height = image.shape[0]
        for cnt in contours:
            area = cv2.contourArea(cnt)
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = h/w
            
            if (area > 2000 and 
                h > img_height * 0.3 and 
                aspect_ratio > 1.5 and 
                w > 30):
                valid_contours.append((x, y, w, h))
        
        valid_contours.sort(key=lambda x: x[0])
        if len(valid_contours) != 8:
            raise ValueError(f"检测到 {len(valid_contours)} 列，应为8列")
            
        columns = []
        for x, y, w, h in valid_contours[:8]:
            column = image[y:y+h, x:x+w]
            columns.append(column)
            
        return columns, valid_contours[:8]
    
    def split_cards(self, image: np.ndarray) -> None:
        # 分割列并获取轮廓信息
        columns, contours = self._split_columns(image)
        
        # 计算单张纸牌高度
        first_column_height = contours[0][3]  # 第一列高度
        fifth_column_height = contours[4][3]  # 第五列高度
        card_height = first_column_height - fifth_column_height
        
        # 从每列中提取单张纸牌
        for col_idx, column in enumerate(columns):
            num_cards = 7 if col_idx < 4 else 6
            column_height = column.shape[0]
            
            for row_idx in range(num_cards):
                # 计算当前纸牌的位置
                start_y = row_idx * card_height
                end_y = start_y + card_height
                
                # 确保不超出图像边界
                if end_y > column_height:
                    end_y = column_height
                
                # 提取单张纸牌
                card = column[start_y:end_y, :]
                
                # 保存图像，使用无损压缩
                filename = f"{col_idx+1}{row_idx+1}.png"
                cv2.imwrite(os.path.join(self.output_dir, filename), card, 
                          [cv2.IMWRITE_PNG_COMPRESSION, 0])

# 添加主函数，使模块可以单独运行
if __name__ == "__main__":
    # 检查Freecell_Layout.png是否存在
    layout_path = "Freecell_Layout.png"
    if not os.path.exists(layout_path):
        print(f"错误: 未找到{layout_path}文件")
        exit(1)
    
    try:
        # 读取图像
        image = cv2.imread(layout_path)
        if image is None:
            print(f"错误: 无法读取图像{layout_path}")
            exit(1)
            
        print(f"正在处理图像: {layout_path}")
        
        # 创建分割器并处理图像
        splitter = CardSplitter()
        splitter.split_cards(image)
        
        print(f"处理完成! 分割后的卡片已保存到{splitter.output_dir}目录")
    except Exception as e:
        print(f"处理过程中出错: {str(e)}")
        exit(1)