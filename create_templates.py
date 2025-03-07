"""
纸牌模板生成工具

功能特征:
1. 界面布局
   - 上方显示2倍放大的图片预览区
   - 下方是13个点数按钮(A23456789TJQK)，3行5列排布
   - 支持鼠标点击和键盘输入(A23456789JQK和1代表10)

2. 处理逻辑
   - 从Card_Rank_Images目录读取待处理的纸牌图像
   - 根据文件名后缀(_r或_b)和点数出现次数确定输出文件名
   - 输出文件命名规则：{点数}_{颜色后缀}_{序号}.png
     例如：4_r_1.png表示红色4点第一次出现
   - 将处理后的图片保存到Card_Rank_Templates目录

3. 验证功能
   - 实时跟踪已处理牌的数量和分布
   - 验证规则：
     * 总牌数必须为52张
     * 红色牌和黑色牌各26张
     * 每种颜色必须包含完整的A23456789TJQK序列各两次
     * 不允许重复牌

4. 辅助功能
   - 显示当前处理进度(X/52)
   - 显示验证结果和错误信息
   - 支持撤销上一步操作
   - 自动跳转到下一张待处理图片

输出格式:
Card_Rank_Templates/
├── AH.png  # 红桃A
├── AS.png  # 黑桃A
├── 2H.png  # 红桃2
└── ...     # 其他纸牌图像

错误处理:
- 重复牌检测和提示
- 非法花色组合警告
- 文件读写异常处理
- 验证失败详细信息
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
        self.root.geometry("900x300")  # 设置窗口大小
        
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
        
        # 创建并清空输出目录
        self.output_dir = 'Card_Rank_Templates'
        if os.path.exists(self.output_dir):
            for file in os.listdir(self.output_dir):
                os.remove(os.path.join(self.output_dir, file))
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 创建界面
        self.create_widgets()
        
        # 加载图片
        self.load_images()
        
        # 绑定键盘事件
        self.root.bind('<Key>', self.handle_key)

    def load_images(self):
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
        if not self.current_image_path:
            return
            
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
        img = cv2.imread(self.current_image_path)
        if img is not None:
            cv2.imwrite(new_path, img)
            self.processed_cards[color_suffix].append(number)
            self.update_progress()
            
            # 更新模板可视化
            # 确定花色
            if color_suffix == '_r':
                suit = 'H' if count == 0 else 'D'
            else:
                suit = 'S' if count == 0 else 'C'
            
            # 更新对应位置的图像
            card_key = f"{number}{suit}"
            if card_key in self.template_labels:
                img_display = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img_display = Image.fromarray(img_display)
                photo = ImageTk.PhotoImage(img_display)
                self.template_labels[card_key].configure(image=photo)
                self.template_labels[card_key].image = photo
            
            # 移动到下一张
            self.current_index += 1
            if self.current_index < len(self.image_files):
                self.load_current_image()
            else:
                self.status_var.set("所有图片处理完成")
                self.validate_results()

    def handle_key(self, event):
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
        elif key == 'T':  # 处理10的输入
            self.process_card('10')
        elif key in '1A':  # 处理A的输入
            self.process_card('A')

    def update_progress(self):
        total = sum(len(cards) for cards in self.processed_cards.values())
        self.progress_var.set(f"进度: {total}/52 张")

    def validate_results(self):
        if sum(len(cards) for cards in self.processed_cards.values()) == 52:
            # 验证完整性
            errors = []
            valid_numbers = set('A23456789TJQK')
            
            for color, numbers in self.processed_cards.items():
                if len(numbers) != 26:
                    errors.append(f"{color}颜色数量错误: {len(numbers)}张")
                
                # 检查每个点数是否出现两次
                for num in valid_numbers:
                    count = numbers.count(num)
                    if count != 2:
                        errors.append(f"{color}颜色的{num}出现{count}次，应为2次")
            
            if errors:
                messagebox.showerror("验证失败", "\n".join(errors))
            else:
                messagebox.showinfo("完成", "所有牌已处理完成，验证通过！")

    def create_widgets(self):
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
        # 状态和进度显示（单行）
        info_frame = ttk.Frame(self.left_frame)
        info_frame.pack(fill=tk.X, pady=5)
        
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        status_label = ttk.Label(info_frame, textvariable=self.status_var)
        status_label.pack(side=tk.LEFT, padx=5)
        
        self.progress_var = tk.StringVar()
        self.update_progress()
        progress_label = ttk.Label(info_frame, textvariable=self.progress_var)
        progress_label.pack(side=tk.RIGHT, padx=5)
        
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