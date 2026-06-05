"""
花色模板生成工具

功能特征:
1. 界面布局
   - 左侧区域：
     * 上方显示2倍放大的花色图片预览区
     * 中间是4个花色按钮(H红桃、S黑桃、D方块、C梅花)
     * 下方显示状态信息和处理进度
   - 右侧区域：
     * 以表格形式显示4种花色的模板状态
   - 支持鼠标点击和键盘输入(H、S、D、C)

2. 处理逻辑
   - 从Card_Suit_Images目录读取待处理的花色图像
   - 支持多组模板集管理，存储在Card_Suit_Templates/set_X目录下
   - 根据文件名后缀(_r或_b)和花色确定输出文件名
   - 输出文件命名规则：{花色}_{颜色后缀}_{序号}.png
     例如：H_r_1.png表示红色花色第一次出现(红桃)
   - 自动检测已有模板集，可以继续处理未完成的模板或创建新模板集

3. 验证功能
   - 实时跟踪已处理花色的数量和分布
   - 验证规则：
     * 总花色数必须为52张
     * 红色花色和黑色花色各26张
     * 每种颜色必须包含完整的HSDC序列各两次
     * 不允许重复花色
   - 提供详细的验证结果对话框，显示当前处理状态和花色分布

输出格式:
Card_Suit_Templates/
├── set_1/                # 第一组模板集
│   ├── H_r_1.png         # 红桃
│   ├── S_b_1.png         # 黑桃
│   ├── D_r_2.png         # 方块
│   └── ...               # 其他花色图像
└── set_2/                # 第二组模板集
    ├── H_r_1.png         # 红桃
    └── ...               # 其他花色图像
"""

import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
import os
from PIL import Image, ImageTk

class SuitTemplateCreator:
    def __init__(self, root):
        self.root = root
        self.root.title("花色模板生成工具")
        self.root.geometry("600x400")
        
        self.left_frame = ttk.Frame(self.root, width=300)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10)
        self.left_frame.pack_propagate(False)
        
        self.right_frame = ttk.Frame(self.root)
        self.right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        
        self.current_image_path = None
        self.current_image = None
        self.image_files = []
        self.current_index = 0
        self.processed_suits = {'_r': [], '_b': []}
        self.template_labels = {}
        self.templates_exist = False
        self.templates_cleared = False
        self.template_set = 1
        self.need_clear_templates = False
        
        self.base_dir = 'Card_Suit_Templates'
        os.makedirs(self.base_dir, exist_ok=True)
        
        self.create_widgets()
        self.load_existing_templates()
        self.load_images()
        self.root.bind('<Key>', self.handle_key)

    def load_existing_templates(self):
        template_sets = self.get_template_sets()
        
        if not template_sets:
            self.template_set = 1
            self.output_dir = os.path.join(self.base_dir, f'set_{self.template_set}')
            os.makedirs(self.output_dir, exist_ok=True)
            return
            
        self.template_set = max(template_sets)
        self.output_dir = os.path.join(self.base_dir, f'set_{self.template_set}')
        
        template_files = [f for f in os.listdir(self.output_dir) if f.endswith('.png')]
        if not template_files:
            return
            
        self.templates_exist = True
        loaded_count = self.load_template_files(template_files)
        
        self.progress_var.set(f"已载入模板: {loaded_count}/52 张")
        self.update_progress()
        
        if loaded_count == 52 and self.validate_suits(show_message=False):
            self.template_set += 1
            self.output_dir = os.path.join(self.base_dir, f'set_{self.template_set}')
            os.makedirs(self.output_dir, exist_ok=True)
            self.status_var.set(f"模板验证通过，新模板将保存到set_{self.template_set}")
            self.need_clear_templates = True
        else:
            self.status_var.set("已加载现有模板，开始处理将提示是否清空")

    def get_template_sets(self):
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
        loaded_count = 0
        for file in template_files:
            try:
                parts = file.split('_')
                if len(parts) != 3:
                    continue
                    
                suit, color = parts[0], parts[1]
                
                template_path = os.path.join(self.output_dir, file)
                self.update_template_image(f"{suit}_{color}", template_path)
                
                self.processed_suits[f"_{color}"].append(suit)
                loaded_count += 1
            except Exception as e:
                print(f"加载模板 {file} 时出错: {str(e)}")
                
        return loaded_count

    def update_template_image(self, card_key, image_path):
        img = cv2.imread(image_path)
        if img is None:
            return
            
        img_display = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_display = Image.fromarray(img_display)
        photo = ImageTk.PhotoImage(img_display)
        self.template_labels[card_key].configure(image=photo)
        self.template_labels[card_key].image = photo

    def clear_templates(self):
        self.processed_suits = {'_r': [], '_b': []}
        self.update_progress()
        
        for key in self.template_labels:
            label = self.template_labels[key]
            label.configure(image='')
            if hasattr(label, 'image'):
                delattr(label, 'image')
            
        self.templates_exist = False
        self.templates_cleared = True
        self.need_clear_templates = False
        
        self.status_var.set(f"已清空模板显示，新模板将保存到set_{self.template_set}")

    def load_images(self):
        input_dir = 'Card_Suit_Images'
        if os.path.exists(input_dir):
            self.image_files = sorted([f for f in os.listdir(input_dir) if f.endswith('.png')])
            if self.image_files:
                self.load_current_image()
            else:
                self.status_var.set("Card_Suit_Images目录为空")
        else:
            self.status_var.set("Card_Suit_Images目录不存在")

    def load_current_image(self):
        if 0 <= self.current_index < len(self.image_files):
            image_path = os.path.join('Card_Suit_Images', self.image_files[self.current_index])
            self.current_image_path = image_path
            
            img = cv2.imread(image_path)
            if img is not None:
                img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(img)
                photo = ImageTk.PhotoImage(img)
                self.preview_label.configure(image=photo)
                self.preview_label.image = photo
                
                self.status_var.set(f"当前图片: {self.image_files[self.current_index]}")
            else:
                self.status_var.set("无法读取图片")

    def process_suit(self, suit):
        if not self.current_image_path:
            return
            
        if self.templates_exist and not self.templates_cleared:
            if messagebox.askyesno("确认操作", "检测到已有模板文件，是否清空并创建新模板？"):
                self.need_clear_templates = True
            else:
                self.status_var.set("操作已取消")
                return
        
        if self.need_clear_templates:
            self.clear_templates()
            
        filename = self.image_files[self.current_index]
        color_suffix = '_r' if '_r.' in filename else '_b'
        
        count = sum(1 for s in self.processed_suits[color_suffix] if s == suit)
        if count >= 2:
            messagebox.showerror("错误", f"{suit}{color_suffix}已存在两次")
            return
            
        new_filename = f"{suit}{color_suffix}_{count + 1}.png"
        new_path = os.path.join(self.output_dir, new_filename)
        
        img = cv2.imread(self.current_image_path)
        if img is None:
            self.status_var.set("无法读取图片")
            return
            
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
            
        cv2.imwrite(new_path, img)
        self.processed_suits[color_suffix].append(suit)
        self.update_progress()
        
        card_key = f"{suit}{color_suffix}"
        if card_key in self.template_labels:
            self.update_template_image(card_key, new_path)
        
        self.move_to_next_image()
    
    def move_to_next_image(self):
        self.current_index += 1
        if self.current_index < len(self.image_files):
            self.load_current_image()
        else:
            self.status_var.set("所有图片处理完成")
            self.validate_results()

    def handle_key(self, event):
        key = event.char.upper()
        if key in 'HSDC':
            self.process_suit(key)

    def update_progress(self):
        total = sum(len(suits) for suits in self.processed_suits.values())
        if self.templates_exist and not self.templates_cleared:
            self.progress_var.set(f"已载入模板: {total}/52 张")
        else:
            self.progress_var.set(f"进度: {total}/52 张")
            
    def validate_suits(self, show_message=True):
        total = sum(len(suits) for suits in self.processed_suits.values())
        
        errors = []
        valid_suits = set('HSDC')
        
        red_count = len(self.processed_suits['_r'])
        black_count = len(self.processed_suits['_b'])
        
        result_info = f"总计: {total}/52 张\n"
        result_info += f"红色花色: {red_count}/26 张\n"
        result_info += f"黑色花色: {black_count}/26 张\n"
        
        if total == 52:
            if red_count != 26:
                errors.append(f"红色花色数量错误: {red_count}张，应为26张")
            if black_count != 26:
                errors.append(f"黑色花色数量错误: {black_count}张，应为26张")
            
            for color, color_name in [('_r', '红色'), ('_b', '黑色')]:
                suits = self.processed_suits[color]
                result_info += f"\n{color_name}花色分布:\n"
                
                for suit in valid_suits:
                    count = suits.count(suit)
                    result_info += f"{suit}: {count}/2 张\n"
                    
                    if count > 2:
                        errors.append(f"{color_name}花色中{suit}出现{count}次，超过了2次")
                    elif count < 2:
                        errors.append(f"{color_name}花色中{suit}出现{count}次，少于2次")
        
        if errors and total == 52 and show_message:
            messagebox.showerror("验证失败", "\n".join(errors))
            self.status_var.set("验证失败")
            return False
        elif total == 52:
            if show_message:
                messagebox.showinfo("验证通过", "所有52张花色验证通过！")
            self.status_var.set("验证通过")
            return True
        else:
            if show_message:
                result_dialog = tk.Toplevel(self.root)
                result_dialog.title("模板加载状态")
                result_dialog.geometry("400x500")
                
                frame = ttk.Frame(result_dialog)
                frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                scrollbar = ttk.Scrollbar(frame)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                text_area = tk.Text(frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
                text_area.pack(fill=tk.BOTH, expand=True)
                scrollbar.config(command=text_area.yview)
                
                text_area.insert(tk.END, result_info)
                text_area.config(state=tk.DISABLED)
                
                close_btn = ttk.Button(result_dialog, text="关闭", command=result_dialog.destroy)
                close_btn.pack(pady=10)
            
            self.status_var.set(f"已处理: {total}/52 张，验证未完成")
            return False
    
    def validate_loaded_templates(self):
        return self.validate_suits(show_message=False)
        
    def validate_results(self):
        return self.validate_suits(show_message=True)

    def create_widgets(self):
        self.preview_label = ttk.Label(self.left_frame)
        self.preview_label.pack(pady=5)
        
        button_frame = ttk.Frame(self.left_frame)
        button_frame.pack(pady=5)
        
        suits = ['H', 'S', 'D', 'C']
        for i, suit in enumerate(suits):
            btn = ttk.Button(button_frame, text=suit, width=5,
                           command=lambda s=suit: self.process_suit(s))
            btn.grid(row=i//2, column=i%2, padx=5, pady=5)
            
        validate_btn = ttk.Button(button_frame, text="验证", width=5,
                                command=lambda: self.validate_suits(show_message=True))
        validate_btn.grid(row=2, column=0, columnspan=2, padx=5, pady=5)
        
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
        
        self.right_frame.grid_columnconfigure(tuple(range(3)), minsize=60)
        self.right_frame.grid_rowconfigure(tuple(range(3)), minsize=60)
        
        suits = ['H', 'S', 'D', 'C']
        
        ttk.Label(self.right_frame, text="花色").grid(row=0, column=0, padx=2)
        ttk.Label(self.right_frame, text="红色").grid(row=0, column=1, padx=2)
        ttk.Label(self.right_frame, text="黑色").grid(row=0, column=2, padx=2)
        
        for i, suit in enumerate(suits):
            ttk.Label(self.right_frame, text=suit).grid(row=i+1, column=0, pady=2)
            
            label_r = ttk.Label(self.right_frame, borderwidth=1, relief="solid")
            label_r.grid(row=i+1, column=1, padx=1, pady=1, sticky="nsew")
            self.template_labels[f"{suit}_r"] = label_r
            
            label_b = ttk.Label(self.right_frame, borderwidth=1, relief="solid")
            label_b.grid(row=i+1, column=2, padx=1, pady=1, sticky="nsew")
            self.template_labels[f"{suit}_b"] = label_b

if __name__ == '__main__':
    root = tk.Tk()
    app = SuitTemplateCreator(root)
    root.mainloop()
