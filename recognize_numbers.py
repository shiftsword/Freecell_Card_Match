"""
FreeCell纸牌数字识别模块

图像特征:
- 输入为单张纸牌的局部图像，主要包含左上角的数字区域
- 数字包括A、2-9、T(10)、J、Q、K
- 颜色分为红色和黑色，通过文件名后缀'_r'和'_b'区分
- 图像已经过预处理和裁剪，边缘清晰

实现方法:
1. 图像预处理
   - 3倍放大提升细节
   - LAB色彩空间CLAHE对比度增强
   - 自适应阈值二值化
   - 形态学处理去噪

2. OCR识别
   - 使用Tesseract OCR引擎
   - PSM 6和10模式提高单字符识别准确率
   - 设置字符白名单和置信度阈值
   - 特殊处理数字10转换为T

3. 布局格式化
   - 按列组织识别结果
   - 红黑色转换为四种花色(HSDC)
   - 输出标准FreeCell布局格式
   - 验证牌组完整性和合法性

4. 输出格式
   标准FreeCell布局格式示例:
   # MS Freecell Game Layout
   #
   : 4H QD 2H 9H TS 6D TC
   : 3S AC TD 5D KD 9C 8H
   : 7D 5S JD QH 9S 6S KS
   : AD 8D 4S KH QS 6H QC
   : JH 9D 2D 5H 7C 4D
   : 7S TH AS 2C KC 2S
   : AH JS 4C 6C 7H 3H
   : 8S JC 5C 8C 3D 3C

5. 完整性和合法性规则
   - 总牌数必须为52张
   - 每种花色(H/S/D/C)各13张
   - 每种花色必须包含完整的A23456789TJQK序列
   - 不允许重复牌
   - 红色牌先H后D，黑色牌先S后C
   - 验证失败时输出具体错误信息

"""

import cv2
import pytesseract
import numpy as np
import os
import time
def recognize_card_number(image_path):
    """识别单张纸牌图像中的数字"""
    start_time = time.time()
    img = cv2.imread(image_path)
    if img is None:
        return None, 0, "无法读取图片", 0
    
    # 恢复3倍放大以提高识别率
    img = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    
    # 使用两种预处理方法
    # 1. 灰度+自适应阈值
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    thresh1 = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY, 15, 5)
    
    # 2. LAB色彩空间增强（对于低对比度图像效果更好）
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl,a,b))
    enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    thresh2 = cv2.threshold(cv2.cvtColor(enhanced, cv2.COLOR_BGR2GRAY), 
                          127, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    
    # 定义OCR配置
    configs = [
        '--psm 10 --oem 3 -c tessedit_char_whitelist=AJQK0123456789 -c tessedit_certainty_threshold=60',
        '--psm 6 --oem 3 -c tessedit_char_whitelist=AJQK0123456789 -c tessedit_certainty_threshold=60'
    ]
    
    best_confidence = 0
    best_result = None
    error_msg = "识别失败"
    
    # 尝试不同的组合
    for thresh in [thresh1, thresh2]:
        for config in configs:
            try:
                # 使用image_to_data获取置信度
                data = pytesseract.image_to_data(thresh, config=config, output_type=pytesseract.Output.DICT)
                if data['text'] and data['conf']:
                    for text, conf in zip(data['text'], data['conf']):
                        text = text.strip().replace('I', '1').replace('i', '1').replace('l', '1').upper()
                        if conf > best_confidence:
                            if text.startswith('1') and len(text) > 1:
                                text = 'T'  # 将10改为T
                            if text == 'T' or text in 'AJQK123456789':
                                best_confidence = conf
                                best_result = text
                                error_msg = ""
            except Exception as e:
                continue
    
    # 如果识别失败，尝试使用更宽松的配置
    if not best_result:
        try:
            # 使用更宽松的配置
            text = pytesseract.image_to_string(thresh1, config='--psm 8 -c tessedit_char_whitelist=AJQK0123456789').strip()
            text = text.strip().replace('I', '1').replace('i', '1').replace('l', '1').upper()
            if text.startswith('1') and len(text) > 1:
                text = 'T'
            if text == 'T' or text in 'AJQK123456789':
                best_result = text
                best_confidence = 80  # 设置一个默认置信度
                error_msg = ""
        except:
            pass
    
    process_time = int((time.time() - start_time) * 1000)
    return best_result, best_confidence, error_msg, process_time
def preprocess_image(img):
    """图像预处理：放大和增强对比度"""
    img = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl,a,b))
    return cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
def normalize_text(text):
    """标准化识别文本"""
    text = text.strip().replace('I', '1').replace('i', '1').replace('l', '1').upper()
    if text.startswith('1') and len(text) > 1:
        text = 'T'  # 将10改为T
    return text
def validate_cards(columns):
    """验证牌组是否完整合法"""
    suits = {'H': [], 'S': [], 'D': [], 'C': []}
    all_cards = []
    for col in columns:
        for card in col:
            number, suit = card[0], card[1]
            suits[suit].append(number)
            all_cards.append(card)
    errors = []
    valid_numbers = set('A23456789TJQK')
    # 检查每种花色
    for suit, numbers in suits.items():
        if len(numbers) != 13:
            errors.append(f"{suit}花色数量错误: {len(numbers)}张")
        
        missing = valid_numbers - set(numbers)
        if missing:
            errors.append(f"{suit}花色缺少: {','.join(sorted(missing))}")
        
        duplicates = [n for n in numbers if numbers.count(n) > 1]
        if duplicates:
            errors.append(f"{suit}花色重复: {','.join(sorted(set(duplicates)))}")
    # 检查总数
    if len(all_cards) != 52:
        errors.append(f"总牌数错误: {len(all_cards)}张")
    return not bool(errors), errors
def format_freecell_layout(results):
    """将识别结果格式化为MS Freecell布局"""
    # 初始化8列，每列7个空位（最大可能的牌数）
    columns = [["  " for _ in range(7)] for _ in range(8)]
    red_first, black_first = {}, {}
    
    # 按文件名排序并分配到对应列
    for result in sorted(results, key=lambda x: x['filename']):
        # 从文件名获取列号和行号
        col = int(result['filename'][0]) - 1
        row = int(result['filename'].split('_')[0][1:]) - 1
        number = result['number']
        color = result['color']
        
        # 转换花色
        if color == 'r':
            suit = 'H' if number not in red_first else 'D'
            red_first[number] = True
        else:
            suit = 'S' if number not in black_first else 'C'
            black_first[number] = True
        
        # 在正确的位置放置卡牌
        columns[col][row] = f"{number}{suit}"
    
    # 格式化输出
    output = ["# MS Freecell Game Layout", "#"]
    for col in columns:
        # 移除末尾的空位，但保留中间的未识别位置
        while col and col[-1] == "  ":
            col.pop()
        output.append(": " + " ".join(col))
    
    # 验证结果
    valid_cards = [card for col in columns for card in col if card != "  "]
    is_valid, errors = validate_cards([valid_cards])
    output.append("")
    if is_valid:
        output.append("# 牌组完整且合法")
    else:
        output.append("# 验证失败:")
        for error in errors:
            output.append(f"# {error}")
    
    return output
def process_all_cards():
    """处理所有纸牌图像并生成布局"""
    start_time = time.time()
    output_dir = 'output'
    if not os.path.exists(output_dir):
        print("output目录不存在")
        return []
    # 初始化
    image_files = sorted([f for f in os.listdir(output_dir) if f.endswith('.png')])
    results = []
    # 清空日志文件
    with open('ocr-result.log', 'w', encoding='utf-8') as f:
        f.write("识别结果,文件名,点数,匹配度,用时,方法\n")
    # 处理每张图片
    for filename in image_files:
        image_path = os.path.join(output_dir, filename)
        number, confidence, error_msg, process_time = recognize_card_number(image_path)
        color = 'r' if '_r.' in filename else 'b'
        # 记录结果
        log_line = create_log_line(filename, number, color, confidence, process_time, error_msg)
        with open('ocr-result.log', 'a', encoding='utf-8') as f:
            f.write(log_line)
        print(log_line.strip())
        if number:
            results.append({'number': number, 'color': color, 'filename': filename})
    # 生成布局
    if results:
        layout = format_freecell_layout(results)
        print("\nFreecell Layout:")
        for line in layout:
            print(line)
        # 追加到日志
        with open('ocr-result.log', 'a', encoding='utf-8') as f:
            f.write("\n")
            for line in layout:
                f.write(line + "\n")
    # 输出统计
    total_time = int((time.time() - start_time) * 1000)
    print(f"\n共识别 {len(results)} 张卡牌，总用时 {total_time}ms")
    return results
def create_log_line(filename, number, color, confidence, process_time, error_msg=""):
    """创建日志行"""
    if number:
        return f"识别成功: {filename} , {number}{color} , [PSM6+10] , [匹配度:{confidence:.1f}%] , [{process_time}ms]\n"
    else:
        return f"识别失败: {filename} , FAIL , [PSM6+10] , [匹配度:0.0%] , [{process_time}ms] - {error_msg}\n"
if __name__ == '__main__':
    results = process_all_cards()