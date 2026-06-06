"""
纸牌点数和花色识别模块 (v3.0 - 整体模板匹配)

优化特性:
1. CombinedTemplateManager - 整体模板管理（点数+花色一起匹配）
2. UnifiedTemplateManager - 分离模板管理（向后兼容）
3. BatchCardMatcher - 批量匹配，颜色约束优化
4. 模板缓存 - 同一模板集只加载一次
5. 向后兼容 - 保留原有 API 接口
"""

import cv2
import numpy as np
import os
import time
from typing import Dict, List, Tuple, Optional

# ============================================================
# 统一模板管理器
# ============================================================

RANK_CHARS = set('A23456789TJQK')
SUIT_CHARS = set('HSDC')
COLOR_SUIT_MAP = {
    '_r': ['H', 'D'],  # 红牌 → 红心/方块
    '_b': ['S', 'C'],  # 黑牌 → 黑桃/梅花
}


class UnifiedTemplateManager:
    """
    统一模板管理器：从 rank_dir 和 suit_dir 一次性加载所有模板。
    
    模板文件命名规则: {label}_{color}_{seq}.png
    - rank: label ∈ {A,2,...,T,J,Q,K}
    - suit: label ∈ {H,S,D,C}
    """
    
    def __init__(self, rank_dir: str, suit_dir: str):
        self.rank_dir = rank_dir
        self.suit_dir = suit_dir
        # {color: [(cv_img, label), ...]}
        self.rank_templates: Dict[str, List[Tuple[np.ndarray, str]]] = {'_r': [], '_b': []}
        self.suit_templates: Dict[str, List[Tuple[np.ndarray, str]]] = {'_r': [], '_b': []}
        self._load_all()
    
    def _load_all(self):
        """一次性加载 rank + suit 模板"""
        self._load_dir(self.rank_dir, self.rank_templates, RANK_CHARS)
        self._load_dir(self.suit_dir, self.suit_templates, SUIT_CHARS)
    
    @staticmethod
    def _load_dir(template_dir: str, 
                  target: Dict[str, List[Tuple[np.ndarray, str]]],
                  valid_labels: set):
        """从目录加载模板，按首字符过滤到对应分类"""
        if not os.path.exists(template_dir):
            return
        
        for file in os.listdir(template_dir):
            if not file.endswith('.png'):
                continue
            parts = file.split('_')
            if len(parts) != 3:
                continue
            
            label, color = parts[0], f"_{parts[1]}"
            if label not in valid_labels:
                continue
            
            img = cv2.imread(os.path.join(template_dir, file), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                target[color].append((img, label))
    
    def get_rank_count(self, color: str) -> int:
        return len(self.rank_templates.get(color, []))
    
    def get_suit_count(self, color: str) -> int:
        return len(self.suit_templates.get(color, []))


class TemplateCache:
    """模板缓存：同一模板集只加载一次"""
    _cache: Dict[str, UnifiedTemplateManager] = {}
    
    @classmethod
    def get(cls, rank_dir: str, suit_dir: str) -> UnifiedTemplateManager:
        key = f"{rank_dir}|{suit_dir}"
        if key not in cls._cache:
            cls._cache[key] = UnifiedTemplateManager(rank_dir, suit_dir)
        return cls._cache[key]
    
    @classmethod
    def clear(cls):
        cls._cache.clear()


# ============================================================
# 整体模板管理器（点数+花色一起匹配）
# ============================================================

CARD_CHARS = set('A23456789TJQK') | set('HSDC')

class CombinedTemplateManager:
    """整体模板管理器：从单一目录加载点数+花色组合模板。
    模板文件命名规则: {rank}{suit}.png (如 AH.png, 2S.png, TC.png)
    """
    
    def __init__(self, template_dir: str):
        self.template_dir = template_dir
        self.templates: Dict[str, List[Tuple[np.ndarray, str]]] = {'_r': [], '_b': []}
        self._load()
    
    def _load(self):
        if not os.path.exists(self.template_dir):
            return
        for file in os.listdir(self.template_dir):
            if not file.endswith('.png'):
                continue
            label = file[:-4]
            if len(label) != 2:
                continue
            rank, suit = label[0], label[1]
            if rank not in RANK_CHARS or suit not in SUIT_CHARS:
                continue
            color = '_r' if suit in 'HD' else '_b'
            img = cv2.imread(os.path.join(self.template_dir, file), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                self.templates[color].append((img, label))


class CombinedTemplateCache:
    _cache: Dict[str, CombinedTemplateManager] = {}
    
    @classmethod
    def get(cls, template_dir: str) -> CombinedTemplateManager:
        if template_dir not in cls._cache:
            cls._cache[template_dir] = CombinedTemplateManager(template_dir)
        return cls._cache[template_dir]
    
    @classmethod
    def clear(cls):
        cls._cache.clear()


class CombinedCardMatcher:
    """整体卡片匹配器：匹配点数+花色组合"""
    
    def __init__(self, template_dir: str,
                 size_threshold: float = 0.3,
                 match_threshold: float = 0.4):
        self.tm = CombinedTemplateCache.get(template_dir)
        self.size_threshold = size_threshold
        self.match_threshold = match_threshold
    
    def match_card(self, info_image: np.ndarray) -> Dict:
        """匹配整体信息图像，返回点数+花色"""
        all_templates = self.tm.templates['_r'] + self.tm.templates['_b']
        if not all_templates:
            return {'rank': None, 'suit': None, 'confidence': 0.0, 'count': 0}
        
        if len(info_image.shape) > 2:
            info_image = cv2.cvtColor(info_image, cv2.COLOR_BGR2GRAY)
        
        best_label = None
        best_score = 0.0
        match_count = 0
        
        for template, label in all_templates:
            match_count += 1
            score, size_score = _match_single(info_image, template, self.size_threshold)
            threshold = self.match_threshold * (0.8 + 0.2 * size_score)
            if score > best_score and score > threshold:
                best_score = score
                best_label = label
        
        if best_label:
            return {
                'rank': best_label[0],
                'suit': best_label[1],
                'confidence': best_score * 100,
                'count': match_count,
            }
        return {'rank': None, 'suit': None, 'confidence': 0.0, 'count': match_count}




def _calculate_size_similarity(img_size: Tuple[int, int], 
                               tmpl_size: Tuple[int, int]) -> float:
    """计算图像尺寸相似度"""
    h_ratio = img_size[0] / tmpl_size[0]
    w_ratio = img_size[1] / tmpl_size[1]
    return 1 - abs(1 - min(h_ratio, w_ratio))


def _match_single(image: np.ndarray, template: np.ndarray, 
                  size_threshold: float = 0.3) -> Tuple[float, float]:
    """与单个模板匹配，返回 (final_score, size_score)"""
    size_score = _calculate_size_similarity(image.shape, template.shape)
    if size_score < size_threshold:
        return 0.0, size_score
    
    resized = cv2.resize(image, (template.shape[1], template.shape[0]))
    result = cv2.matchTemplate(resized, template, cv2.TM_CCOEFF_NORMED)
    match_score = np.max(result)
    return match_score * size_score, size_score


def _match_against_templates(image: np.ndarray, 
                             templates: List[Tuple[np.ndarray, str]],
                             size_threshold: float = 0.3,
                             match_threshold: float = 0.4) -> Tuple[Optional[str], float, int]:
    """
    在模板列表中找到最佳匹配。
    返回 (best_label, confidence_percent, match_count)
    """
    if image is None or not templates:
        return None, 0.0, 0
    
    if len(image.shape) > 2:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    best_label = None
    best_score = 0.0
    match_count = 0
    
    for template, label in templates:
        match_count += 1
        score, size_score = _match_single(image, template, size_threshold)
        
        # 动态阈值：尺寸越接近，阈值越宽松
        threshold = match_threshold * (0.8 + 0.2 * size_score)
        
        if score > best_score and score > threshold:
            best_score = score
            best_label = label
    
    return best_label, best_score * 100, match_count


# ============================================================
# 批量匹配器
# ============================================================

class BatchCardMatcher:
    """
    批量匹配器：
    - 一次性加载模板（缓存）
    - 颜色约束优化：红牌只匹配 H/D，黑牌只匹配 S/C
    - size_ratio 预计算
    """
    
    def __init__(self, rank_dir: str, suit_dir: str,
                 rank_size_threshold: float = 0.3,
                 rank_match_threshold: float = 0.4,
                 suit_size_threshold: float = 0.1,
                 suit_match_threshold: float = 0.5):
        self.tm = TemplateCache.get(rank_dir, suit_dir)
        self.rank_size_threshold = rank_size_threshold
        self.rank_match_threshold = rank_match_threshold
        self.suit_size_threshold = suit_size_threshold
        self.suit_match_threshold = suit_match_threshold
    
    def match_rank(self, image: np.ndarray, color: str) -> Tuple[Optional[str], float, int]:
        """匹配点数"""
        return _match_against_templates(
            image, self.tm.rank_templates[color],
            self.rank_size_threshold, self.rank_match_threshold
        )
    
    def match_suit(self, image: np.ndarray, color: str,
                   allowed_suits: Optional[List[str]] = None) -> Tuple[Optional[str], float, int]:
        """
        匹配花色。
        allowed_suits: 如果指定，只在这些花色中搜索（颜色约束优化）
        """
        templates = self.tm.suit_templates[color]
        
        if allowed_suits is not None:
            templates = [(img, label) for img, label in templates if label in allowed_suits]
        
        return _match_against_templates(
            image, templates,
            self.suit_size_threshold, self.suit_match_threshold
        )
    
    def match_card(self, rank_image: np.ndarray, suit_image: Optional[np.ndarray],
                   color: str) -> Dict:
        """匹配单张卡片（点数 + 花色），利用颜色约束。"""
        rank, rank_conf, rank_count = self.match_rank(rank_image, color)
        allowed = COLOR_SUIT_MAP.get(color)
        suit, suit_conf, suit_count = 0.0, 0.0, 0
        if suit_image is not None:
            suit, suit_conf, suit_count = self.match_suit(suit_image, color, allowed)
        return {
            'rank': rank, 'rank_confidence': rank_conf, 'rank_count': rank_count,
            'suit': suit, 'suit_confidence': suit_conf, 'suit_count': suit_count,
        }
    
    def match_info_card(self, info_image: np.ndarray, color: str,
                        rank_ratio: float = 0.45) -> Dict:
        """从整体信息图像分割并匹配点数和花色。
        rank_ratio: 点数区域占整体图像高度的比例
        """
        h = info_image.shape[0]
        split = int(h * rank_ratio)
        rank_img = info_image[0:split, :]
        suit_img = info_image[split:, :]
        return self.match_card(rank_img, suit_img, color)


# ============================================================
# 模板集自动选择
# ============================================================

def _find_best_template_dir(base_dir: str, preferred: str) -> Optional[str]:
    """在 base_dir 中找到最佳可用模板集"""
    preferred_path = os.path.join(base_dir, preferred)
    if os.path.exists(preferred_path) and os.listdir(preferred_path):
        return preferred_path
    
    # 回退：找任意可用的
    if os.path.exists(base_dir):
        for d in sorted(os.listdir(base_dir)):
            dir_path = os.path.join(base_dir, d)
            if d.startswith('set_') and os.path.isdir(dir_path) and os.listdir(dir_path):
                return dir_path
    return None


def resolve_template_dirs(template_set: str = 'auto', 
                          card_width: int = 0, card_height: int = 0) -> Tuple[Optional[str], Optional[str]]:
    """
    根据模板集名称或卡片尺寸，解析出 rank_dir 和 suit_dir。
    
    返回 (rank_dir, suit_dir)，任一可能为 None。
    """
    rank_base = 'Card_Rank_Templates'
    suit_base = 'Card_Suit_Templates'
    
    if template_set == 'auto':
        if card_width >= 200 or card_height >= 80:
            template_set = 'set_2880x1800'
        else:
            template_set = 'set_1920x1080'
    
    rank_dir = _find_best_template_dir(rank_base, template_set)
    
    # suit 模板集名称可能与 rank 不同（如 set_1920x1080 → set_1）
    suit_dir = _find_best_template_dir(suit_base, template_set)
    if suit_dir is None and template_set == 'set_1920x1080':
        suit_dir = _find_best_template_dir(suit_base, 'set_1')
    
    return rank_dir, suit_dir


# ============================================================
# 向后兼容 API（原有接口保持不变）
# ============================================================

class TemplateManager:
    """向后兼容：点数模板管理器"""
    def __init__(self, template_dir: str = 'Card_Rank_Templates/set_1920x1080'):
        self.template_dir = template_dir
        self.templates: Dict[str, List[Tuple[np.ndarray, str]]] = {'_r': [], '_b': []}
        self._load()
    
    def _load(self):
        if not os.path.exists(self.template_dir):
            return
        for file in os.listdir(self.template_dir):
            if not file.endswith('.png'):
                continue
            parts = file.split('_')
            if len(parts) != 3:
                continue
            rank, color = parts[0], f"_{parts[1]}"
            if rank not in RANK_CHARS:
                continue
            img = cv2.imread(os.path.join(self.template_dir, file), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                self.templates[color].append((img, rank))


class SuitTemplateManager:
    """向后兼容：花色模板管理器"""
    def __init__(self, template_dir: str = 'Card_Suit_Templates/set_1'):
        self.template_dir = template_dir
        self.templates: Dict[str, List[Tuple[np.ndarray, str]]] = {'_r': [], '_b': []}
        self._load()
    
    def _load(self):
        if not os.path.exists(self.template_dir):
            return
        for file in os.listdir(self.template_dir):
            if not file.endswith('.png'):
                continue
            parts = file.split('_')
            if len(parts) != 3:
                continue
            suit, color = parts[0], f"_{parts[1]}"
            if suit not in SUIT_CHARS:
                continue
            img = cv2.imread(os.path.join(self.template_dir, file), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                self.templates[color].append((img, suit))


class RankMatcher:
    """向后兼容：点数匹配器"""
    def __init__(self, template_manager: TemplateManager):
        self.tm = template_manager
    
    def match_rank(self, image: np.ndarray, color: str) -> Tuple[Optional[str], float, int]:
        return _match_against_templates(image, self.tm.templates[color])


class SuitMatcher:
    """向后兼容：花色匹配器"""
    def __init__(self, template_manager: SuitTemplateManager):
        self.tm = template_manager
    
    def match_suit(self, image: np.ndarray, color: str) -> Tuple[Optional[str], float, int]:
        return _match_against_templates(image, self.tm.templates[color],
                                        size_threshold=0.1, match_threshold=0.5)


def match_card_rank(image_path: str, template_dir: str = 'Card_Rank_Templates/set_1') -> Tuple[Optional[str], float, int, int]:
    """向后兼容：匹配单张卡片点数"""
    start_time = time.time()
    try:
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError(f"无法读取图像: {image_path}")
        
        color = '_r' if '_r.' in image_path else '_b'
        
        # 尝试首选模板集
        tm = TemplateManager(template_dir)
        matcher = RankMatcher(tm)
        result, confidence, match_count = matcher.match_rank(image, color)
        
        # 回退：尝试其他模板集
        if result is None:
            template_base = 'Card_Rank_Templates'
            if os.path.exists(template_base):
                for d in sorted(os.listdir(template_base)):
                    alt_dir = os.path.join(template_base, d)
                    if d.startswith('set_') and os.path.isdir(alt_dir) and alt_dir != template_dir:
                        try:
                            alt_tm = TemplateManager(alt_dir)
                            alt_matcher = RankMatcher(alt_tm)
                            alt_result, alt_conf, alt_count = alt_matcher.match_rank(image, color)
                            match_count += alt_count
                            if alt_result is not None:
                                result, confidence = alt_result, alt_conf
                                break
                        except:
                            continue
        
        process_time = int((time.time() - start_time) * 1000)
        return result, confidence, match_count, process_time
    except Exception as e:
        print(f"错误: {str(e)}")
        return None, 0.0, 0, int((time.time() - start_time) * 1000)


def match_card_suit(image_path: str, template_dir: str = 'Card_Suit_Templates/set_1') -> Tuple[Optional[str], float, int, int]:
    """向后兼容：匹配单张卡片花色"""
    start_time = time.time()
    try:
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError(f"无法读取图像: {image_path}")
        
        color = '_r' if '_r.' in image_path else '_b'
        
        tm = SuitTemplateManager(template_dir)
        matcher = SuitMatcher(tm)
        result, confidence, match_count = matcher.match_suit(image, color)
        
        if result is None:
            template_base = 'Card_Suit_Templates'
            if os.path.exists(template_base):
                for d in sorted(os.listdir(template_base)):
                    alt_dir = os.path.join(template_base, d)
                    if d.startswith('set_') and os.path.isdir(alt_dir) and alt_dir != template_dir:
                        try:
                            alt_tm = SuitTemplateManager(alt_dir)
                            alt_matcher = SuitMatcher(alt_tm)
                            alt_result, alt_conf, alt_count = alt_matcher.match_suit(image, color)
                            match_count += alt_count
                            if alt_result is not None:
                                result, confidence = alt_result, alt_conf
                                break
                        except:
                            continue
        
        process_time = int((time.time() - start_time) * 1000)
        return result, confidence, match_count, process_time
    except Exception as e:
        print(f"错误: {str(e)}")
        return None, 0.0, 0, int((time.time() - start_time) * 1000)


# ============================================================
# 新 API：批量处理（推荐使用）
# ============================================================

def process_all_cards_v2(rank_template_dir: str,
                         suit_template_dir: str) -> Tuple[List[Dict], int]:
    """批量处理所有卡片（使用统一模板管理器）。
    返回: (results, total_time_ms)
    """
    start_time = time.time()
    
    info_dir = 'Card_Info_Images'
    if not os.path.exists(info_dir):
        print(f"{info_dir}目录不存在")
        return [], 0
    
    matcher = BatchCardMatcher(rank_template_dir, suit_template_dir)
    
    image_files = sorted([f for f in os.listdir(info_dir) if f.endswith('.png')])
    results = []
    
    for filename in image_files:
        card_start = time.time()
        info_path = os.path.join(info_dir, filename)
        color = '_r' if '_r.' in filename else '_b'
        
        info_img = cv2.imread(info_path, cv2.IMREAD_GRAYSCALE)
        if info_img is None:
            continue
        
        match_result = matcher.match_info_card(info_img, color)
        
        number = match_result['rank']
        suit = match_result['suit']
        if suit is None:
            suit = 'H' if color == '_r' else 'S'
        
        card_time = int((time.time() - card_start) * 1000)
        results.append({
            'number': number, 'suit': suit, 'color': color, 'filename': filename,
            'rank_confidence': match_result['rank_confidence'],
            'suit_confidence': match_result['suit_confidence'],
            'time_ms': card_time,
        })
    
    return results, int((time.time() - start_time) * 1000)


def process_all_cards_v2_legacy(rank_template_dir: str,
                                suit_template_dir: str) -> Tuple[List[Dict], int]:
    """批量处理所有卡片（从 Card_Rank_Images 和 Card_Suit_Images）。
    返回: (results, total_time_ms)
    """
    start_time = time.time()
    
    rank_dir = 'Card_Rank_Images'
    suit_dir = 'Card_Suit_Images'
    if not os.path.exists(rank_dir):
        print(f"{rank_dir}目录不存在")
        return [], 0
    
    matcher = BatchCardMatcher(rank_template_dir, suit_template_dir)
    
    image_files = sorted([f for f in os.listdir(rank_dir) if f.endswith('.png')])
    results = []
    
    for filename in image_files:
        card_start = time.time()
        rank_path = os.path.join(rank_dir, filename)
        suit_path = os.path.join(suit_dir, filename)
        color = '_r' if '_r.' in filename else '_b'
        
        rank_img = cv2.imread(rank_path, cv2.IMREAD_GRAYSCALE)
        suit_img = None
        if os.path.exists(suit_path):
            suit_img = cv2.imread(suit_path, cv2.IMREAD_GRAYSCALE)
        
        match_result = matcher.match_card(rank_img, suit_img, color)
        
        number = match_result['rank']
        suit = match_result['suit']
        if suit is None:
            suit = 'H' if color == '_r' else 'S'
        
        card_time = int((time.time() - card_start) * 1000)
        results.append({
            'number': number, 'suit': suit, 'color': color, 'filename': filename,
            'rank_confidence': match_result['rank_confidence'],
            'suit_confidence': match_result['suit_confidence'],
            'time_ms': card_time,
        })
    
    return results, int((time.time() - start_time) * 1000)


def process_all_cards_combined(template_dir: str) -> Tuple[List[Dict], int]:
    """批量处理所有卡片（使用整体模板）。
    返回: (results, total_time_ms)
    """
    start_time = time.time()
    
    cards_dir = 'Single_Card_Images'
    if not os.path.exists(cards_dir):
        print(f"{cards_dir}目录不存在")
        return [], 0
    
    matcher = CombinedCardMatcher(template_dir)
    
    image_files = sorted([f for f in os.listdir(cards_dir) if f.endswith('.png')])
    results = []
    
    for filename in image_files:
        card_start = time.time()
        card_path = os.path.join(cards_dir, filename)
        
        card_img = cv2.imread(card_path)
        if card_img is None:
            continue
        
        h, w = card_img.shape[:2]
        crop_w = int(w * 0.25)
        info_region = card_img[0:h, 0:crop_w]
        gray = cv2.cvtColor(info_region, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)
        kernel = np.ones((2, 2), np.uint8)
        binary = cv2.dilate(binary, kernel, iterations=1)
        binary = cv2.erode(binary, kernel, iterations=1)
        info_img = cv2.bitwise_not(binary)
        info_img[info_img < 128] = 0
        info_img[info_img >= 128] = 255
        
        match_result = matcher.match_card(info_img)
        
        number = match_result['rank'] or '?'
        suit = match_result['suit'] or '?'
        
        card_time = int((time.time() - card_start) * 1000)
        results.append({
            'number': number, 'suit': suit, 'color': '', 'filename': filename,
            'rank_confidence': match_result['confidence'],
            'suit_confidence': match_result['confidence'],
            'time_ms': card_time,
        })
    
    return results, int((time.time() - start_time) * 1000)


def process_all_cards(rank_template_dir: str = 'Card_Rank_Templates/set_1920x1080',
                      suit_template_dir: str = 'Card_Suit_Templates/set_1'):
    """向后兼容：处理所有卡片"""
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
    
    # 使用新的批量处理
    results_v2, _ = process_all_cards_v2(rank_template_dir, suit_template_dir or '')
    
    # 转换为旧格式
    results = []
    for r in results_v2:
        results.append({
            'number': r['number'],
            'suit': r['suit'],
            'color': r['color'],
            'filename': r['filename'],
        })
    
    if results:
        layout = format_freecell_layout(results)
        print("\nFreecell Layout:")
        for line in layout:
            print(line)
        
        with open('Card_Match_Result.log', 'a', encoding='utf-8') as f:
            f.write("\n")
            for line in layout:
                f.write(line + "\n")
    
    success_count = sum(1 for r in results if r['number'])
    total_time = int((time.time() - start_time) * 1000)
    print(f"\n共识别成功 {success_count} 张卡牌，总用时 {total_time}ms")
    return results


# ============================================================
# 布局生成与验证
# ============================================================

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
            if len(card) >= 2 and card.strip() != "":
                number, suit = card[0], card[1]
                if suit in suits:
                    suits[suit].append(number)
                    all_cards.append(card)
    
    errors = []
    valid_numbers = set('A23456789TJQK')
    for suit, numbers in suits.items():
        if len(numbers) != 13:
            errors.append(f"{suit}花色数量错误: {len(numbers)}张")
        missing = valid_numbers - set(numbers)
        if missing:
            errors.append(f"{suit}花色缺少: {','.join(sorted(missing))}")
        duplicates = [n for n in numbers if numbers.count(n) > 1]
        if duplicates:
            errors.append(f"{suit}花色重复: {','.join(sorted(set(duplicates)))}")
    if len(all_cards) != 52:
        errors.append(f"总牌数错误: {len(all_cards)}张")
    return not bool(errors), errors


def results_to_columns(results):
    columns = [["  " for _ in range(7)] for _ in range(8)]
    
    for result in sorted(results, key=lambda x: x['filename']):
        filename = result['filename']
        name = filename.split('.')[0]  # 去掉扩展名
        parts = name.split('_')
        pos = parts[0]  # 取第一部分（位置信息）
        
        if len(pos) >= 2 and pos[0].isdigit():
            col = int(pos[0]) - 1
            row = int(pos[1:]) - 1 if pos[1:].isdigit() else 0
            number = result['number']
            suit = result.get('suit', 'H')
            
            if 0 <= col < 8 and 0 <= row < 7:
                columns[col][row] = f"{number}{suit}"
    
    return columns


def format_columns_to_text(columns, include_validation=True):
    """将列布局格式化为文本"""
    layout_lines = []
    layout_lines.append("# MS Freecell Game Layout")
    layout_lines.append("#")
    
    for i in range(8):
        cards_in_column = [card for card in columns[i] if card.strip()]
        line = ": " + " ".join(cards_in_column)
        layout_lines.append(line)
    
    is_valid, errors = validate_cards(columns)
    
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


if __name__ == '__main__':
    results = process_all_cards()
