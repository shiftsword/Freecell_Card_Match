"""
纸牌点数和花色识别模块

功能特征:
1. 识别对象
   - 识别Card_Rank_Images中的纸牌点数图像
   - 识别Card_Suit_Images中的纸牌花色图像
   - 固定字符集：A23456789TJQK（13个字符）
   - 花色字符集：H(红心)、S(黑桃)、D(方块)、C(梅花)

2. 匹配策略
   - 基于尺寸的初步筛选
   - 多模板评分机制
   - 动态阈值调整

3. 输入输出
   - 输入：Card_Rank_Images和Card_Suit_Images目录中的图像
   - 输出：识别结果（点数和花色）
   - 模板来源：Card_Rank_Templates和Card_Suit_Templates目录
"""

import cv2
import numpy as np
import os
import time
from typing import Dict, List, Tuple, Optional

class TemplateManager:
    def __init__(self, template_dir: str = 'Card_Rank_Templates/set_1920*1080'):
        self.template_dir = template_dir
        self.templates: Dict[str, List[Tuple[np.ndarray, str]]] = {'_r': [], '_b': []}
        self.load_templates()

    def load_templates(self):
        if not os.path.exists(self.template_dir):
            raise FileNotFoundError(f"模板目录不存在: {self.template_dir}")

        for file in os.listdir(self.template_dir):
            if not file.endswith('.png'):
                continue

            parts = file.split('_')
            if len(parts) != 3:
                continue

            rank, color = parts[0], f"_{parts[1]}"
            template_path = os.path.join(self.template_dir, file)
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

            if template is not None:
                self.templates[color].append((template, rank))


class SuitTemplateManager:
    def __init__(self, template_dir: str = 'Card_Suit_Templates/set_1'):
        self.template_dir = template_dir
        self.templates: Dict[str, List[Tuple[np.ndarray, str]]] = {'_r': [], '_b': []}
        self.load_templates()

    def load_templates(self):
        if not os.path.exists(self.template_dir):
            raise FileNotFoundError(f"花色模板目录不存在: {self.template_dir}")

        for file in os.listdir(self.template_dir):
            if not file.endswith('.png'):
                continue

            parts = file.split('_')
            if len(parts) != 3:
                continue

            suit, color = parts[0], f"_{parts[1]}"
            template_path = os.path.join(self.template_dir, file)
            template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

            if template is not None:
                self.templates[color].append((template, suit))


class SuitMatcher:
    def __init__(self, template_manager: SuitTemplateManager):
        self.template_manager = template_manager
        self.size_threshold = 0.1
        self.match_threshold = 0.5

    def calculate_size_similarity(self, img_size: Tuple[int, int], 
                                tmpl_size: Tuple[int, int]) -> float:
        h_ratio = img_size[0] / tmpl_size[0]
        w_ratio = img_size[1] / tmpl_size[1]
        return 1 - abs(1 - min(h_ratio, w_ratio))

    def match_single_template(self, image: np.ndarray, 
                            template: np.ndarray) -> Tuple[float, float]:
        size_score = self.calculate_size_similarity(image.shape, template.shape)
        if size_score < self.size_threshold:
            return 0.0, size_score

        resized_image = cv2.resize(image, (template.shape[1], template.shape[0]))
        result = cv2.matchTemplate(resized_image, template, cv2.TM_CCOEFF_NORMED)
        match_score = np.max(result)

        final_score = match_score * size_score
        return final_score, size_score

    def match_suit(self, image: np.ndarray, color: str) -> Tuple[Optional[str], float, int]:
        if image is None:
            return None, 0.0, 0

        if len(image.shape) > 2:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        best_suit = None
        best_score = 0
        match_count = 0
        
        for template, suit in self.template_manager.templates[color]:
            match_count += 1
            score, size_score = self.match_single_template(image, template)
            
            threshold = self.match_threshold * (0.8 + 0.2 * size_score)
            
            if score > best_score and score > threshold:
                best_score = score
                best_suit = suit

        return best_suit, best_score * 100, match_count

class RankMatcher:
    def __init__(self, template_manager: TemplateManager):
        self.template_manager = template_manager
        self.size_threshold = 0.3
        self.match_threshold = 0.4

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
    start_time = time.time()
    try:
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError(f"无法读取图像: {image_path}")

        color = '_r' if '_r.' in image_path else '_b'

        template_manager = TemplateManager(template_dir)
        matcher = RankMatcher(template_manager)
        result, confidence, match_count = matcher.match_rank(image, color)
        
        if result is None:
            template_base = 'Card_Rank_Templates'
            if os.path.exists(template_base):
                for d in sorted(os.listdir(template_base)):
                    alt_dir = os.path.join(template_base, d)
                    if d.startswith('set_') and os.path.isdir(alt_dir) and alt_dir != template_dir:
                        try:
                            alt_manager = TemplateManager(alt_dir)
                            alt_matcher = RankMatcher(alt_manager)
                            alt_result, alt_confidence, alt_count = alt_matcher.match_rank(image, color)
                            match_count += alt_count
                            if alt_result is not None:
                                result, confidence = alt_result, alt_confidence
                                break
                        except:
                            continue
            
        process_time = int((time.time() - start_time) * 1000)
        return result, confidence, match_count, process_time

    except Exception as e:
        print(f"错误: {str(e)}")
        process_time = int((time.time() - start_time) * 1000)
        return None, 0.0, 0, process_time


def match_card_suit(image_path: str, template_dir: str = 'Card_Suit_Templates/set_1') -> Tuple[Optional[str], float, int, int]:
    start_time = time.time()
    try:
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError(f"无法读取图像: {image_path}")

        color = '_r' if '_r.' in image_path else '_b'

        template_manager = SuitTemplateManager(template_dir)
        matcher = SuitMatcher(template_manager)
        result, confidence, match_count = matcher.match_suit(image, color)
        
        if result is None:
            template_base = 'Card_Suit_Templates'
            if os.path.exists(template_base):
                for d in sorted(os.listdir(template_base)):
                    alt_dir = os.path.join(template_base, d)
                    if d.startswith('set_') and os.path.isdir(alt_dir) and alt_dir != template_dir:
                        try:
                            alt_manager = SuitTemplateManager(alt_dir)
                            alt_matcher = SuitMatcher(alt_manager)
                            alt_result, alt_confidence, alt_count = alt_matcher.match_suit(image, color)
                            match_count += alt_count
                            if alt_result is not None:
                                result, confidence = alt_result, alt_confidence
                                break
                        except:
                            continue
            
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
    columns = [["  " for _ in range(7)] for _ in range(8)]
    
    for result in sorted(results, key=lambda x: x['filename']):
        parts = result['filename'].split('_')[0]
        if len(parts) >= 2 and parts[0].isdigit():
            col = int(parts[0]) - 1
            row = int(parts[1:]) - 1 if parts[1:].isdigit() else 0
            number = result['number']
            suit = result.get('suit', 'H')
            
            if 0 <= col < 8 and 0 <= row < 7:
                columns[col][row] = f"{number}{suit}"
    
    return columns

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
    columns = results_to_columns(results)
    layout_lines, is_valid, errors = format_columns_to_text(columns)
    
    clipboard_lines = layout_lines[:-2] if is_valid else layout_lines[:-2-len(errors)]
    
    if root and is_valid:
        try:
            clipboard_text = "\n".join(clipboard_lines)
            root.clipboard_clear()
            root.clipboard_append(clipboard_text)
            root.update()
            print("\n布局已自动复制到剪贴板")
        except Exception as e:
            print(f"\n复制到剪贴板失败: {str(e)}")
    
    return layout_lines
def process_all_cards(rank_template_dir: str = 'Card_Rank_Templates/set_1920x1080', 
                      suit_template_dir: str = 'Card_Suit_Templates/set_1'):
    start_time = time.time()
    
    rank_dir = 'Card_Rank_Images'
    suit_dir = 'Card_Suit_Images'
    
    if not os.path.exists(rank_dir):
        print(f"{rank_dir}目录不存在")
        return []
    
    if not os.path.exists(suit_dir):
        print(f"{suit_dir}目录不存在")
        return []
    
    if not os.path.exists(rank_template_dir):
        template_base = 'Card_Rank_Templates'
        available_sets = []
        if os.path.exists(template_base):
            for d in os.listdir(template_base):
                dir_path = os.path.join(template_base, d)
                if d.startswith('set_') and os.path.isdir(dir_path) and os.listdir(dir_path):
                    available_sets.append(d)
        
        if available_sets:
            rank_template_dir = os.path.join(template_base, available_sets[0])
            print(f"使用可用的点数模板集: {rank_template_dir}")
        else:
            print(f"错误: 未找到可用的点数模板集")
            return []
    
    if not os.path.exists(suit_template_dir):
        template_base = 'Card_Suit_Templates'
        available_sets = []
        if os.path.exists(template_base):
            for d in os.listdir(template_base):
                dir_path = os.path.join(template_base, d)
                if d.startswith('set_') and os.path.isdir(dir_path) and os.listdir(dir_path):
                    available_sets.append(d)
        
        if available_sets:
            suit_template_dir = os.path.join(template_base, available_sets[0])
            print(f"使用可用的花色模板集: {suit_template_dir}")
        else:
            print(f"警告: 未找到可用的花色模板集，将使用默认花色")
            suit_template_dir = None
    
    image_files = sorted([f for f in os.listdir(rank_dir) if f.endswith('.png')])
    results = []
    success_count = 0
    
    with open('Card_Match_Result.log', 'w', encoding='utf-8') as f:
        f.write("识别结果,文件名,点数,花色,匹配度,用时\n")
    
    for filename in image_files:
        rank_path = os.path.join(rank_dir, filename)
        suit_path = os.path.join(suit_dir, filename)
        
        number, rank_confidence, rank_count, rank_time = match_card_rank(rank_path, rank_template_dir)
        color = 'r' if '_r.' in filename else 'b'
        
        suit = None
        suit_confidence = 0
        suit_time = 0
        if suit_template_dir and os.path.exists(suit_path):
            suit, suit_confidence, suit_count, suit_time = match_card_suit(suit_path, suit_template_dir)
        
        if suit is None:
            if color == 'r':
                suit = 'H'
            else:
                suit = 'S'
        
        error_msg = "识别失败" if number is None else ""
        log_line = f"识别成功: {filename} , {number}{suit} , [{rank_confidence:.1f}%] , [{rank_time + suit_time}ms]\n"
        if number is None:
            log_line = f"识别失败: {filename} , FAIL , [0.0%] , [{rank_time + suit_time}ms]\n"
        
        with open('Card_Match_Result.log', 'a', encoding='utf-8') as f:
            f.write(log_line)
        print(log_line.strip())
        
        if number:
            results.append({'number': number, 'suit': suit, 'color': color, 'filename': filename})
            success_count += 1
    
    if results:
        layout = format_freecell_layout(results)
        print("\nFreecell Layout:")
        for line in layout:
            print(line)
        
        with open('Card_Match_Result.log', 'a', encoding='utf-8') as f:
            f.write("\n")
            for line in layout:
                f.write(line + "\n")
    
    total_time = int((time.time() - start_time) * 1000)
    print(f"\n共识别成功 {success_count} 张卡牌，总用时 {total_time}ms")
    return results

if __name__ == '__main__':
    # 当直接运行时，使用默认的高分辨率模板集
    results = process_all_cards()