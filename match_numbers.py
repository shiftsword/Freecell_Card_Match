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
    def __init__(self, template_dir: str = 'Card_Rank_Templates/set_1920*1080'):  # 修改默认模板路径
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

def match_card_rank(image_path: str, template_dir: str = 'Card_Rank_Templates/set_1') -> Tuple[Optional[str], float, int, int]:
    """主函数：识别单张纸牌图像的点数，返回点数、匹配度、匹配次数和处理时间
    
    Args:
        image_path: 图像路径
        template_dir: 模板目录路径，默认为'Card_Rank_Templates/set_1'
    """
    start_time = time.time()
    try:
        # 初始化，使用传入的模板目录
        template_manager = TemplateManager(template_dir)
        matcher = RankMatcher(template_manager)

        # 读取图像
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError(f"无法读取图像: {image_path}")

        # 确定颜色
        color = '_r' if '_r.' in image_path else '_b'

        # 执行匹配
        result, confidence, match_count = matcher.match_rank(image, color)
            
        process_time = int((time.time() - start_time) * 1000)
        return result, confidence, match_count, process_time

    except Exception as e:
        print(f"错误: {str(e)}")
        process_time = int((time.time() - start_time) * 1000)
        return None, 0.0, 0, process_time

def create_log_line(filename, number, color, confidence, match_count, process_time, error_msg=""):
    """创建日志行"""
    if number:
        return f"识别成功: {filename} , {number}{color} , [{confidence:.1f}%] , [{process_time}ms]\n"
    else:
        return f"识别失败: {filename} , FAIL , [0.0%] , [{process_time}ms] - {error_msg}\n"

def validate_cards(columns):
    """验证牌组是否完整合法"""
    suits = {'H': [], 'S': [], 'D': [], 'C': []}
    all_cards = []
    for col in columns:
        for card in col:
            if len(card) >= 2 and card.strip() != "":  # 确保卡片格式正确且不是空白
                number, suit = card[0], card[1]
                # 检查花色是否有效
                if suit in suits:
                    suits[suit].append(number)
                    all_cards.append(card)
                # 如果遇到无效花色，跳过该卡片
    
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

# 新增函数：将结果列表转换为列布局
def results_to_columns(results):
    """将识别结果列表转换为列布局
    
    Args:
        results: 识别结果列表
    
    Returns:
        columns: 8列纸牌布局
        red_first, black_first: 用于跟踪花色分配
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
    
    return columns, red_first, black_first

# 新增函数：格式化列布局为文本
def format_columns_to_text(columns, include_validation=True):
    """将列布局格式化为文本
    
    Args:
        columns: 8列纸牌布局
        include_validation: 是否包含验证结果
    
    Returns:
        layout_lines: 格式化后的布局文本行
        is_valid: 布局是否有效
        errors: 验证错误列表
    """
    # 格式化输出
    layout_lines = []
    layout_lines.append("# MS Freecell Game Layout")
    layout_lines.append("#")
    
    # 添加8行纸牌布局，去除每行末尾的空格
    for i in range(8):
        cards_in_column = [card for card in columns[i] if card.strip()]  # 只保留非空卡片
        line = ": " + " ".join(cards_in_column)
        layout_lines.append(line)
    
    # 验证牌组是否完整合法
    is_valid, errors = validate_cards(columns)
    
    # 添加验证结果
    if include_validation:
        layout_lines.append("")
        if is_valid:
            layout_lines.append("# 牌组完整且合法")
        else:
            layout_lines.append("# 牌组不完整或不合法")
            for error in errors:
                layout_lines.append(f"# {error}")
    
    return layout_lines, is_valid, errors

def format_freecell_layout(results, root=None):
    """将识别结果格式化为MS Freecell布局
    
    Args:
        results: 识别结果列表
        root: 可选的Tkinter根窗口，用于剪贴板操作
    """
    # 转换结果为列布局
    columns, _, _ = results_to_columns(results)
    
    # 格式化为文本
    layout_lines, is_valid, errors = format_columns_to_text(columns)
    
    # 复制到剪贴板的内容不包含验证结果
    clipboard_lines = layout_lines[:-2] if is_valid else layout_lines[:-2-len(errors)]
    
    # 如果提供了root，则复制到剪贴板
    if root and is_valid:
        try:
            clipboard_text = "\n".join(clipboard_lines)
            root.clipboard_clear()
            root.clipboard_append(clipboard_text)
            root.update()
            print("\n布局已自动复制到剪贴板")
        except Exception as e:
            print(f"\n复制到剪贴板失败: {str(e)}")
    
    return layout_lines  # 返回完整的布局行（包括验证结果）
def process_all_cards(template_dir: str = 'Card_Rank_Templates/set_1920x1080'):  # 修改默认模板路径
    """处理所有纸牌图像并生成布局
    
    Args:
        template_dir: 模板目录路径，默认为'Card_Rank_Templates/set_1920x1080'
    """
    start_time = time.time()
    input_dir = 'Card_Rank_Images'
    if not os.path.exists(input_dir):
        print(f"{input_dir}目录不存在")
        return []
    
    # 检查模板目录是否存在
    if not os.path.exists(template_dir):
        # 尝试查找可用的模板集
        template_base = 'Card_Rank_Templates'
        available_sets = []
        if os.path.exists(template_base):
            for d in os.listdir(template_base):
                dir_path = os.path.join(template_base, d)
                if d.startswith('set_') and os.path.isdir(dir_path) and os.listdir(dir_path):
                    available_sets.append(d)
        
        if available_sets:
            template_dir = os.path.join(template_base, available_sets[0])
            print(f"使用可用的模板集: {template_dir}")
        else:
            print(f"错误: 未找到可用的模板集")
            return []
    
    # 初始化
    image_files = sorted([f for f in os.listdir(input_dir) if f.endswith('.png')])
    results = []
    success_count = 0
    
    # 清空日志文件
    with open('Card_Match_Result.log', 'w', encoding='utf-8') as f:
        f.write("识别结果,文件名,点数,匹配度,用时\n")
    
    # 处理每张图片
    for filename in image_files:
        image_path = os.path.join(input_dir, filename)
        # 传入模板目录
        number, confidence, match_count, process_time = match_card_rank(image_path, template_dir)
        color = 'r' if '_r.' in filename else 'b'
        
        # 记录结果
        error_msg = "识别失败" if number is None else ""
        log_line = create_log_line(filename, number, color, confidence, match_count, process_time, error_msg)
        with open('Card_Match_Result.log', 'a', encoding='utf-8') as f:
            f.write(log_line)
        print(log_line.strip())
        
        if number:
            results.append({'number': number, 'color': color, 'filename': filename})
            success_count += 1
    
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
    print(f"\n共识别成功 {success_count} 张卡牌，总用时 {total_time}ms")
    return results

if __name__ == '__main__':
    # 当直接运行时，使用默认的高分辨率模板集
    results = process_all_cards()