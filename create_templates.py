"""
纸牌模板生成工具

功能特征:
1. 界面布局
   - 左侧区域：
     * 上方显示2倍放大的图片预览区
     * 中间是13个点数按钮(A23456789TJQK)，3行5列排布，右下角为验证按钮
     * 下方显示状态信息和处理进度
   - 右侧区域：
     * 以表格形式显示52张牌的模板状态(4行13列)
     * 行表示花色(H红桃、S黑桃、D方块、C梅花)，列表示点数(A23456789TJQK)
   - 支持鼠标点击和键盘输入(A23456789JQK，1或A代表A，T或0代表10)
   - 数字键盘特殊键：/代表J，*代表Q，-代表K

2. 处理逻辑
   - 从Card_Rank_Images目录读取待处理的纸牌图像
   - 支持多组模板集管理，存储在Card_Rank_Templates/set_X目录下
   - 根据文件名后缀(_r或_b)和点数出现次数确定输出文件名和花色
   - 输出文件命名规则：{点数}_{颜色后缀}_{序号}.png
     例如：4_r_1.png表示红色4点第一次出现(红桃)，4_r_2.png表示第二次出现(方块)
   - 自动检测已有模板集，可以继续处理未完成的模板或创建新模板集

3. 验证功能
   - 实时跟踪已处理牌的数量和分布
   - 验证规则：
     * 总牌数必须为52张
     * 红色牌和黑色牌各26张
     * 每种颜色必须包含完整的A23456789TJQK序列各两次
     * 不允许重复牌
   - 提供详细的验证结果对话框，显示当前处理状态和点数分布

4. 辅助功能
   - 显示当前处理进度(X/52)和状态信息
   - 显示验证结果和错误信息
   - 自动跳转到下一张待处理图片
   - 模板集管理：
     * 自动加载现有模板集
     * 验证完整模板集后自动准备创建新模板集
     * 支持清空现有模板并重新开始

输出格式:
Card_Rank_Templates/
├── set_1/                # 第一组模板集
│   ├── A_r_1.png         # 红桃A
│   ├── A_b_1.png         # 黑桃A
│   ├── 2_r_1.png         # 红桃2
│   └── ...               # 其他纸牌图像
└── set_2/                # 第二组模板集
    ├── A_r_1.png         # 红桃A
    └── ...               # 其他纸牌图像

错误处理:
- 重复牌检测和提示
- 模板加载异常处理
- 文件读写异常处理
- 验证失败详细信息展示
- 模板集管理的状态提示
"""

import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
import os
from PIL import Image, ImageTk

class TemplateCreator:
    def __init__(self, root):
        self.root = root
        self.root.title("纸牌模板生成工具")
        self.root.geometry("900x300")  # 调整窗口宽度以适应表格
        
        # 创建左右分栏
        self.left_frame = ttk.Frame(self.root, width=300)  # 设置左侧宽度
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        self.left_frame.pack_propagate(False)  # 固定左侧宽度
        
        self.right_frame = ttk.Frame(self.root)
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        # 初始化变量
        self.current_image_path = None
        self.current_image = None
        self.image_files = []
        self.current_index = 0
        self.processed_cards = {'_r': [], '_b': []}
        self.template_labels = {}  # 存储模板图像标签
        self.templates_exist = False  # 标记是否存在模板
        self.templates_cleared = False  # 标记是否已清空模板
        self.template_set = 1  # 当前模板集编号
        self.need_clear_templates = False  # 标记是否需要清空模板（在用户开始输入后）
        
        # 设置基础输出目录和当前模板集目录
        self.base_dir = 'Card_Rank_Templates'
        os.makedirs(self.base_dir, exist_ok=True)
        
        # 创建界面
        self.create_widgets()
        
        # 检查并加载现有模板
        self.load_existing_templates()
        
        # 加载待处理图片
        self.load_images()
        
        # 绑定键盘事件
        self.root.bind('<Key>', self.handle_key)

    def load_existing_templates(self):
        """检查并加载现有模板"""
        # 检查是否有模板集目录
        template_sets = self.get_template_sets()
        
        if not template_sets:
            # 没有模板集，创建set_1
            self.template_set = 1
            self.output_dir = os.path.join(self.base_dir, f'set_{self.template_set}')
            os.makedirs(self.output_dir, exist_ok=True)
            return
            
        # 使用最新的模板集
        self.template_set = max(template_sets)
        self.output_dir = os.path.join(self.base_dir, f'set_{self.template_set}')
        
        # 检查模板集是否有文件
        template_files = [f for f in os.listdir(self.output_dir) if f.endswith('.png')]
        if not template_files:
            return
            
        # 加载现有模板
        self.templates_exist = True
        loaded_count = self.load_template_files(template_files)
        
        # 更新进度显示
        self.progress_var.set(f"已载入模板: {loaded_count}/52 张")
        self.update_progress()
        
        # 验证已加载模板
        if loaded_count == 52 and self.validate_cards(show_message=False):
            # 模板集完整且有效，准备创建新模板集
            self.template_set += 1
            self.output_dir = os.path.join(self.base_dir, f'set_{self.template_set}')
            os.makedirs(self.output_dir, exist_ok=True)
            self.status_var.set(f"模板验证通过，新模板将保存到set_{self.template_set}")
            
            # 标记需要在用户开始输入时清空模板
            self.need_clear_templates = True
        else:
            self.status_var.set("已加载现有模板，开始处理将提示是否清空")

    def get_template_sets(self):
        """获取所有模板集编号"""
        if not os.path.exists(self.base_dir):
            return []
            
        sets = []
        for d in os.listdir(self.base_dir):
            if d.startswith('set_') and os.path.isdir(os.path.join(self.base_dir, d)):
                try:
                    set_num = int(d.split('_')[1])
                    sets.append(set_num)
                except (IndexError, ValueError):
                    continue
        return sets

    def load_template_files(self, template_files):
        """加载模板文件并更新界面"""
        loaded_count = 0
        for file in template_files:
            try:
                # 解析文件名获取点数和颜色
                parts = file.split('_')
                if len(parts) != 3:
                    continue
                    
                rank, color = parts[0], parts[1]
                
                # 确定花色
                if color == 'r':
                    suit = 'H' if parts[2].startswith('1') else 'D'
                else:
                    suit = 'S' if parts[2].startswith('1') else 'C'
                
                # 更新对应位置的图像
                card_key = f"{rank}{suit}"
                if card_key not in self.template_labels:
                    continue
                    
                template_path = os.path.join(self.output_dir, file)
                self.update_template_image(card_key, template_path)
                
                # 更新处理记录
                self.processed_cards[f"_{color}"].append(rank)
                loaded_count += 1
            except Exception as e:
                print(f"加载模板 {file} 时出错: {str(e)}")
                
        return loaded_count

    def update_template_image(self, card_key, image_path):
        """更新模板图像显示
        
        Args:
            card_key: 牌的标识，如"AH"
            image_path: 图像文件路径
        """
        img = cv2.imread(image_path)
        if img is None:
            return
            
        img_display = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_display = Image.fromarray(img_display)
        photo = ImageTk.PhotoImage(img_display)
        self.template_labels[card_key].configure(image=photo)
        self.template_labels[card_key].image = photo  # 保持引用

    def clear_templates(self):
        """清空内存中的模板数据"""
        # 重置处理记录
        self.processed_cards = {'_r': [], '_b': []}
        self.update_progress()
        
        # 清空模板显示和引用
        for key in self.template_labels:
            label = self.template_labels[key]
            label.configure(image='')
            if hasattr(label, 'image'):
                delattr(label, 'image')
            
        # 重置模板状态
        self.templates_exist = False
        self.templates_cleared = True
        self.need_clear_templates = False
        
        self.status_var.set(f"已清空模板显示，新模板将保存到set_{self.template_set}")

    def load_images(self):
        """加载待处理的图片"""
        input_dir = 'Card_Rank_Images'
        if os.path.exists(input_dir):
            self.image_files = sorted([f for f in os.listdir(input_dir) if f.endswith('.png')])
            if self.image_files:
                self.load_current_image()
            else:
                self.status_var.set("Card_Rank_Images目录为空")
        else:
            self.status_var.set("Card_Rank_Images目录不存在")

    def load_current_image(self):
        """加载当前索引的图片"""
        if 0 <= self.current_index < len(self.image_files):
            # 读取并显示图片
            image_path = os.path.join('Card_Rank_Images', self.image_files[self.current_index])
            self.current_image_path = image_path
            
            # 使用OpenCV读取图片
            img = cv2.imread(image_path)
            if img is not None:
                # 放大2倍
                img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                # 转换为PIL格式
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(img)
                # 转换为PhotoImage
                photo = ImageTk.PhotoImage(img)
                self.preview_label.configure(image=photo)
                self.preview_label.image = photo
                
                self.status_var.set(f"当前图片: {self.image_files[self.current_index]}")
            else:
                self.status_var.set("无法读取图片")

    def process_card(self, number):
        """处理当前图片为指定点数的牌"""
        if not self.current_image_path:
            return
            
        # 检查是否需要清空现有模板
        if self.templates_exist and not self.templates_cleared:
            if messagebox.askyesno("确认操作", "检测到已有模板文件，是否清空并创建新模板？"):
                self.need_clear_templates = True
            else:
                self.status_var.set("操作已取消")
                return
        
        # 如果需要清空模板，在用户第一次输入时执行
        if self.need_clear_templates:
            self.clear_templates()
            
        # 将10转换为T用于文件名
        if number == '10':
            number = 'T'
            
        # 获取颜色类型
        filename = self.image_files[self.current_index]
        color_suffix = '_r' if '_r.' in filename else '_b'
        
        # 计算序号
        count = sum(1 for card in self.processed_cards[color_suffix] if card == number)
        if count >= 2:
            messagebox.showerror("错误", f"{number}{color_suffix}已存在两次")
            return
            
        # 保存模板
        new_filename = f"{number}{color_suffix}_{count + 1}.png"
        new_path = os.path.join(self.output_dir, new_filename)
        
        # 读取并保存图像
        img = cv2.imread(self.current_image_path)
        if img is None:
            self.status_var.set("无法读取图片")
            return
            
        # 确保输出目录存在
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
            
        cv2.imwrite(new_path, img)
        self.processed_cards[color_suffix].append(number)
        self.update_progress()
        
        # 确定花色并更新模板显示
        suit = self.get_suit_from_color_and_count(color_suffix, count)
        card_key = f"{number}{suit}"
        
        if card_key in self.template_labels:
            self.update_template_image(card_key, new_path)
        
        # 移动到下一张
        self.move_to_next_image()
    
    def get_suit_from_color_and_count(self, color_suffix, count):
        """根据颜色和计数确定花色
        
        Args:
            color_suffix: 颜色后缀 '_r' 或 '_b'
            count: 当前计数 (0 或 1)
            
        Returns:
            str: 花色字符 'H', 'D', 'S' 或 'C'
        """
        if color_suffix == '_r':
            return 'H' if count == 0 else 'D'
        else:
            return 'S' if count == 0 else 'C'
    
    def move_to_next_image(self):
        """移动到下一张图片"""
        self.current_index += 1
        if self.current_index < len(self.image_files):
            self.load_current_image()
        else:
            self.status_var.set("所有图片处理完成")
            self.validate_results()

    def handle_key(self, event):
        """处理键盘输入事件"""
        key = event.char.upper()
        if key in '23456789JQK':
            self.process_card(key)
        elif key == 'T' or key == '0':  # 处理10的输入
            self.process_card('10')
        elif key in '1A':  # 处理A的输入
            self.process_card('A')
        elif key == '/':  # 数字键盘/键输入J
            self.process_card('J')
        elif key == '*':  # 数字键盘*键输入Q
            self.process_card('Q')
        elif key == '-':  # 数字键盘-键输入K
            self.process_card('K')

    def update_progress(self):
        """更新进度显示"""
        total = sum(len(cards) for cards in self.processed_cards.values())
        if self.templates_exist and not self.templates_cleared:
            self.progress_var.set(f"已载入模板: {total}/52 张")
        else:
            self.progress_var.set(f"进度: {total}/52 张")
            
    def validate_cards(self, show_message=True):
        """验证纸牌是否符合规则
        
        Args:
            show_message: 是否显示验证消息对话框
        
        Returns:
            bool: 验证是否通过
        """
        total = sum(len(cards) for cards in self.processed_cards.values())
        
        # 验证完整性
        errors = []
        valid_numbers = set('A23456789TJQK')
        
        # 检查红黑牌数量
        red_count = len(self.processed_cards['_r'])
        black_count = len(self.processed_cards['_b'])
        
        # 准备详细信息
        result_info = f"总计: {total}/52 张\n"
        result_info += f"红色牌: {red_count}/26 张\n"
        result_info += f"黑色牌: {black_count}/26 张\n"
        
        # 只有在总数为52时才检查颜色分布
        if total == 52:
            if red_count != 26:
                errors.append(f"红色牌数量错误: {red_count}张，应为26张")
            if black_count != 26:
                errors.append(f"黑色牌数量错误: {black_count}张，应为26张")
            
            # 检查每种颜色的点数分布
            for color, color_name in [('_r', '红色'), ('_b', '黑色')]:
                numbers = self.processed_cards[color]
                result_info += f"\n{color_name}牌点数分布:\n"
                
                for num in valid_numbers:
                    count = numbers.count(num)
                    result_info += f"{num}: {count}/2 张\n"
                    
                    if count > 2:
                        errors.append(f"{color_name}牌中{num}出现{count}次，超过了2次")
                    elif count < 2:
                        errors.append(f"{color_name}牌中{num}出现{count}次，少于2次")
        
        # 显示验证结果
        if errors and total == 52 and show_message:
            messagebox.showerror("验证失败", "\n".join(errors))
            self.status_var.set("验证失败")
            return False
        elif total == 52:
            if show_message:
                messagebox.showinfo("验证通过", "所有52张牌验证通过！")
            self.status_var.set("验证通过")
            return True
        else:
            # 显示详细的验证结果
            if show_message:
                result_dialog = tk.Toplevel(self.root)
                result_dialog.title("模板加载状态")
                result_dialog.geometry("400x500")
                
                # 添加滚动文本区域
                frame = ttk.Frame(result_dialog)
                frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                scrollbar = ttk.Scrollbar(frame)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                text_area = tk.Text(frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
                text_area.pack(fill=tk.BOTH, expand=True)
                scrollbar.config(command=text_area.yview)
                
                text_area.insert(tk.END, result_info)
                text_area.config(state=tk.DISABLED)
                
                # 添加关闭按钮
                close_btn = ttk.Button(result_dialog, text="关闭", command=result_dialog.destroy)
                close_btn.pack(pady=10)
            
            self.status_var.set(f"已处理: {total}/52 张，验证未完成")
            return False
    
    def validate_loaded_templates(self):
        """验证已加载的模板"""
        return self.validate_cards(show_message=False)
        
    def validate_results(self):
        """验证处理完成的结果"""
        return self.validate_cards(show_message=True)

    def create_widgets(self):
        """创建界面组件"""
        # 左侧区域
        # 图像预览区
        self.preview_label = ttk.Label(self.left_frame)
        self.preview_label.pack(pady=5)
        
        # 按钮区域（3行5列）
        button_frame = ttk.Frame(self.left_frame)
        button_frame.pack(pady=5)
        
        # 点数按钮
        self.buttons = {}
        numbers = ['A', '2', '3', '4', '5', 
                  '6', '7', '8', '9', '10',
                  'J', 'Q', 'K']
        for i, num in enumerate(numbers):
            row = i // 5
            col = i % 5
            btn = ttk.Button(button_frame, text=num, width=5,
                           command=lambda n=num: self.process_card(n))
            btn.grid(row=row, column=col, padx=5, pady=5)
            self.buttons[num] = btn
            
        # 添加验证按钮
        validate_btn = ttk.Button(button_frame, text="验证", width=5,
                                command=lambda: self.validate_cards(show_message=True))
        validate_btn.grid(row=2, column=4, padx=5, pady=5)
        
        # 状态和进度显示（改为两行）
        info_frame = ttk.Frame(self.left_frame)
        info_frame.pack(fill=tk.X, pady=5)
        
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_label = ttk.Label(info_frame, textvariable=self.status_var)
        status_label.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        
        self.progress_var = tk.StringVar()
        self.progress_var.set("进度: 0/52 张")
        progress_label = ttk.Label(info_frame, textvariable=self.progress_var)
        progress_label.pack(side=tk.TOP, fill=tk.X, padx=5)
        
        # 右侧区域 - 模板可视化
        # 设置表格大小
        self.right_frame.grid_columnconfigure(tuple(range(14)), minsize=40)  # 设置列宽
        self.right_frame.grid_rowconfigure(tuple(range(5)), minsize=40)     # 设置行高
        
        numbers = ['A', '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K']
        suits = ['H', 'S', 'D', 'C']
        
        # 添加点数表头
        for i, num in enumerate(numbers):
            ttk.Label(self.right_frame, text=num).grid(row=0, column=i+1, padx=2)
        
        # 添加花色表头和模板显示区域
        for i, suit in enumerate(suits):
            ttk.Label(self.right_frame, text=suit).grid(row=i+1, column=0, pady=2)
            for j, num in enumerate(numbers):
                label = ttk.Label(self.right_frame, borderwidth=1, relief="solid")
                label.grid(row=i+1, column=j+1, padx=1, pady=1, sticky="nsew")
                self.template_labels[f"{num}{suit}"] = label

if __name__ == '__main__':
    root = tk.Tk()
    app = TemplateCreator(root)
    root.mainloop()