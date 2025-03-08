"""
纸牌点数识别模块

功能特征:
1. 识别对象
   - 识别Card_Rank_Images中的纸牌点数图像
   - 固定字符集：A23456789TJQK（13个字符）
   - 白底黑字二值图像
   - 每种点数有4个模板（红黑各两个）

2. 匹配策略
   - 基于尺寸的初步筛选
     * 比较输入图像与模板尺寸
     * 建立模板优先级列表
     * 跳过尺寸差异过大的模板

   - 多模板评分机制
     * 使用同色的4个模板进行匹配
     * 使用归一化相关系数计算匹配分数
     * 评分权重考虑尺寸相似度、匹配质量和模板可靠性

   - 决策过程
     * 综合同一点数的多个模板得分
     * 使用动态阈值（基于尺寸匹配程度调整）
     * 设置最低可信度要求

3. 输入输出
   - 输入：Card_Rank_Images目录中的单个点数图像
   - 输出：识别结果（A-K中的一个字符）
   - 模板来源：Card_Rank_Templates目录

4. 错误处理
   - 图像读取异常处理
   - 匹配失败处理
   - 置信度过低警告
"""

import cv2
import numpy as np
import os
import time
from typing import Dict, List, Tuple, Optional

class TemplateManager:
    def __init__(self, template_dir: str = 'Card_Rank_Templates/set_1'):  # 修改默认模板路径
        self.template_dir = template_dir
        self.templates: Dict[str, List[Tuple[np.ndarray, str]]] = {'_r': [], '_b': []}
        self.load_templates()

    def load_templates(self):
        """加载所有模板并按颜色分类"""
        if not os.path.exists(self.template_dir):
            raise FileNotFoundError(f"模板目录不存在: {self.template_dir}")

        for file in os.listdir(self.template_dir):
            if not file.endswith('.png'):
                continue

            # 解析文件名获取点数和颜色
            parts = file.split('_')
            if len(parts) != 3:
                continue

            rank, color = parts[0], f"_{parts[1]}"
            template_path = os.path.join(self.template_dir, file)
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

            if template is not None:
                self.templates[color].append((template, rank))

class RankMatcher:
    def __init__(self, template_manager: TemplateManager):
        self.template_manager = template_manager
        self.size_threshold = 0.3  # 尺寸差异阈值
        self.match_threshold = 0.7  # 匹配度阈值

    def calculate_size_similarity(self, img_size: Tuple[int, int], 
                                tmpl_size: Tuple[int, int]) -> float:
        """计算图像尺寸相似度"""
        h_ratio = img_size[0] / tmpl_size[0]
        w_ratio = img_size[1] / tmpl_size[1]
        return 1 - abs(1 - min(h_ratio, w_ratio))

    def match_single_template(self, image: np.ndarray, 
                            template: np.ndarray) -> Tuple[float, float]:
        """与单个模板进行匹配"""
        # 计算尺寸相似度
        size_score = self.calculate_size_similarity(image.shape, template.shape)
        if size_score < self.size_threshold:
            return 0.0, size_score

        # 调整图像尺寸以匹配模板
        resized_image = cv2.resize(image, (template.shape[1], template.shape[0]))
        
        # 模板匹配
        result = cv2.matchTemplate(resized_image, template, cv2.TM_CCOEFF_NORMED)
        match_score = np.max(result)

        # 综合评分
        final_score = match_score * size_score
        return final_score, size_score

    def match_rank(self, image: np.ndarray, color: str) -> Tuple[Optional[str], float, int]:
        """识别图像中的点数，返回点数、匹配度和匹配次数"""
        if image is None:
            return None, 0.0, 0

        # 确保图像是灰度图
        if len(image.shape) > 2:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        best_rank = None
        best_score = 0
        match_count = 0
        
        # 对每个点数的所有模板进行匹配
        for template, rank in self.template_manager.templates[color]:
            match_count += 1
            score, size_score = self.match_single_template(image, template)
            
            # 动态调整阈值
            threshold = self.match_threshold * (0.8 + 0.2 * size_score)
            
            if score > best_score and score > threshold:
                best_score = score
                best_rank = rank

        return best_rank, best_score * 100, match_count  # 转换为百分比

def match_card_rank(image_path: str) -> Tuple[Optional[str], float, int, int]:
    """主函数：识别单张纸牌图像的点数，返回点数、匹配度、匹配次数和处理时间"""
    start_time = time.time()
    try:
        # 初始化
        template_manager = TemplateManager()
        matcher = RankMatcher(template_manager)

        # 读取图像
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError(f"无法读取图像: {image_path}")

        # 确定颜色
        color = '_r' if '_r.' in image_path else '_b'

        # 执行匹配
        result, confidence, match_count = matcher.match_rank(image, color)
        if result is None:
            print(f"警告: 无法识别点数 - {image_path}")
            
        process_time = int((time.time() - start_time) * 1000)
        return result, confidence, match_count, process_time

    except Exception as e:
        print(f"错误: {str(e)}")
        process_time = int((time.time() - start_time) * 1000)
        return None, 0.0, 0, process_time

def create_log_line(filename, number, color, confidence, match_count, process_time, error_msg=""):
    """创建日志行"""
    if number:
        return f"识别成功: {filename} , {number}{color} , [模板匹配] , [匹配度:{confidence:.1f}%] , [匹配次数:{match_count}] , [{process_time}ms]\n"
    else:
        return f"识别失败: {filename} , FAIL , [模板匹配] , [匹配度:0.0%] , [匹配次数:{match_count}] , [{process_time}ms] - {error_msg}\n"

def validate_cards(columns):
    """验证牌组是否完整合法"""
    suits = {'H': [], 'S': [], 'D': [], 'C': []}
    all_cards = []
    for col in columns:
        for card in col:
            if len(card) >= 2:  # 确保卡片格式正确
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
def format_freecell_layout(results, root=None):
    """将识别结果格式化为MS Freecell布局
    
    Args:
        results: 识别结果列表
        root: 可选的Tkinter根窗口，用于剪贴板操作
    """
    # 初始化8列，每列7个空位（最大可能的牌数）
    columns = [["  " for _ in range(7)] for _ in range(8)]
    red_first, black_first = {}, {}
    
    # 按文件名排序并分配到对应列
    for result in sorted(results, key=lambda x: x['filename']):
        # 从文件名获取列号和行号
        parts = result['filename'].split('_')[0]
        if len(parts) >= 2 and parts[0].isdigit():
            col = int(parts[0]) - 1
            row = int(parts[1:]) - 1 if parts[1:].isdigit() else 0
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
            if 0 <= col < 8 and 0 <= row < 7:
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
        # 验证成功后自动复制到剪贴板
        try:
            layout_text = "\n".join(output)
            
            # 如果提供了root参数，使用它来操作剪贴板
            if root:
                root.clipboard_clear()
                root.clipboard_append(layout_text)
                root.update()  # 刷新剪贴板
                print("布局已自动复制到剪贴板")
            else:
                # 兼容旧代码，创建临时Tkinter实例
                import tkinter as tk
                temp_root = tk.Tk()
                temp_root.withdraw()  # 隐藏窗口
                temp_root.clipboard_clear()
                temp_root.clipboard_append(layout_text)
                temp_root.update()  # 刷新剪贴板
                temp_root.destroy()
                print("布局已自动复制到剪贴板")
        except Exception as e:
            print(f"复制到剪贴板失败: {str(e)}")
    else:
        output.append("# 验证失败:")
        for error in errors:
            output.append(f"# {error}")
    
    return output
def process_all_cards():
    """处理所有纸牌图像并生成布局"""
    start_time = time.time()
    input_dir = 'Card_Rank_Images'
    if not os.path.exists(input_dir):
        print(f"{input_dir}目录不存在")
        return []
    
    # 初始化
    image_files = sorted([f for f in os.listdir(input_dir) if f.endswith('.png')])
    results = []
    
    # 清空日志文件
    with open('Card_Match_Result.log', 'w', encoding='utf-8') as f:
        f.write("识别结果,文件名,点数,匹配度,匹配次数,用时,方法\n")
    
    # 处理每张图片
    for filename in image_files:
        image_path = os.path.join(input_dir, filename)
        number, confidence, match_count, process_time = match_card_rank(image_path)
        color = 'r' if '_r.' in filename else 'b'
        
        # 记录结果
        error_msg = "识别失败" if number is None else ""
        log_line = create_log_line(filename, number, color, confidence, match_count, process_time, error_msg)
        with open('Card_Match_Result.log', 'a', encoding='utf-8') as f:
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
        with open('Card_Match_Result.log', 'a', encoding='utf-8') as f:
            f.write("\n")
            for line in layout:
                f.write(line + "\n")
    
    # 输出统计
    total_time = int((time.time() - start_time) * 1000)
    print(f"\n共识别 {len(results)} 张卡牌，总用时 {total_time}ms")
    return results

if __name__ == '__main__':
    results = process_all_cards()