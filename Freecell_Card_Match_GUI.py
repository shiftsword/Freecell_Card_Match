import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import cv2
import numpy as np
import threading
import time
from PIL import Image, ImageTk, ImageGrab
import re

# 导入项目模块
from card_splitter import CardSplitter
import extract_numbers
import match_numbers

class FreecellOCRApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FreeCell OCR 纸牌识别系统")
        self.root.geometry("900x700")
        self.root.resizable(True, True)
        
        # 设置图标（如果有的话）
        # self.root.iconbitmap('icon.ico')
        
        # 初始化变量
        self.image_path = tk.StringVar()
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        self.processing = False
        self.current_image = None
        self.template_set = tk.StringVar()
        
        # 创建界面组件
        self.create_widgets()
        
        # 检查必要的目录
        self.check_directories()
        
        # 加载模板集选项
        self.load_template_sets()
    def create_template(self):
        """打开模板创建工具"""
        try:
            # 检查是否已选择图片
            image_path = self.image_path.get()
            if not image_path or not os.path.exists(image_path):
                messagebox.showinfo("提示", "请先选择有效的图像文件")
                return
                
            # 保存当前图像为Freecell_Layout.png
            self.save_current_image_as_layout()
                
            # 自动执行卡片分割和数字提取
            self.result_text.delete(1.0, tk.END)
            self.result_text.insert(tk.END, "正在准备模板创建...\n")
            
            # 步骤1: 分割纸牌
            self.update_status("准备模板: 分割纸牌...")
            # 使用numpy读取图像以支持中文路径
            image = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                raise Exception("无法读取图像")
            
            splitter = CardSplitter()
            splitter.split_cards(image)
            self.update_result("✓ 纸牌分割完成，已保存到Single_Card_Images目录\n")
            
            # 步骤2: 提取数字
            self.update_status("准备模板: 提取数字...")
            extract_numbers.process_cards()
            self.update_result("✓ 数字提取完成，已保存到Card_Rank_Images目录\n")
            
            # 导入模板创建模块
            import create_templates
            import importlib
            importlib.reload(create_templates)  # 确保加载最新版本
                
            # 创建新窗口运行模板创建工具
            template_window = tk.Toplevel(self.root)
            app = create_templates.TemplateCreator(template_window)
                
            # 设置模态窗口
            template_window.transient(self.root)
            template_window.grab_set()
                
            # 等待窗口关闭后重新加载模板集
            self.root.wait_window(template_window)
            self.load_template_sets()
            
            self.update_status("就绪")
                
        except Exception as e:
            messagebox.showerror("错误", f"启动模板创建工具失败: {str(e)}")
            self.update_status(f"处理失败: {str(e)}")
    def check_directories(self):
        """检查并创建必要的目录"""
        # 清空并重建目录
        dirs = ["Single_Card_Images", "Card_Rank_Images"]  # 修改为实际使用的目录名
        for dir_name in dirs:
            if os.path.exists(dir_name):
                for file in os.listdir(dir_name):
                    os.remove(os.path.join(dir_name, file))
            os.makedirs(dir_name, exist_ok=True)
    def load_template_sets(self):
        """加载可用的模板集"""
        template_dir = 'Card_Rank_Templates'
        if not os.path.exists(template_dir):
            os.makedirs(template_dir, exist_ok=True)
            self.template_set.set("自动")  # 默认设置为自动
            return
            
        # 获取所有模板集并删除空目录
        template_sets = []
        for d in os.listdir(template_dir):
            dir_path = os.path.join(template_dir, d)
            if d.startswith('set_') and os.path.isdir(dir_path):
                # 检查目录是否为空
                if not os.listdir(dir_path):
                    # 删除空目录
                    os.rmdir(dir_path)
                    continue
                template_sets.append(d)
            
        # 添加"自动"选项
        template_sets.insert(0, "自动")
        
        if not template_sets or len(template_sets) == 1:
            self.template_set.set("自动")  # 默认设置为自动
        else:
            # 默认选择自动
            self.template_set.set("自动")
            # 更新下拉菜单
            self.template_combo['values'] = template_sets
            
    def check_card_size_and_select_template(self):
        """根据单张纸牌尺寸选择合适的模板集"""
        card_dir = "Single_Card_Images"
        if not os.path.exists(card_dir) or not os.listdir(card_dir):
            return "set_1"  # 默认模板集
        
        # 获取第一张卡片的尺寸
        card_files = [f for f in os.listdir(card_dir) if f.endswith('.png')]
        if not card_files:
            return "set_1"
            
        first_card = os.path.join(card_dir, card_files[0])
        img = cv2.imread(first_card)
        if img is None:
            return "set_1"
        
        height, width = img.shape[:2]
        self.update_result(f"检测到单张纸牌尺寸: {width}x{height}\n")
        
        # 根据单张纸牌尺寸选择模板集
        if width >= 200 or height >= 80:  # 高分辨率卡片 (约2880x1440分辨率)
            template_set = "set_2880x1800"
        else:  # 标准分辨率卡片 (约1920x1080分辨率)
            template_set = "set_1920x1080"
        
        # 检查选择的模板集是否存在，如果不存在则使用可用的模板集
        template_dir = os.path.join('Card_Rank_Templates', template_set)
        if not os.path.exists(template_dir) or not os.listdir(template_dir):
            # 查找可用的模板集
            available_sets = []
            for d in os.listdir('Card_Rank_Templates'):
                dir_path = os.path.join('Card_Rank_Templates', d)
                if d.startswith('set_') and os.path.isdir(dir_path) and os.listdir(dir_path):
                    available_sets.append(d)
            
            if available_sets:
                template_set = available_sets[0]  # 使用第一个可用的模板集
            else:
                template_set = "set_1"  # 如果没有可用的模板集，使用默认值
        
        self.update_result(f"自动选择模板集: {template_set}\n")
        return template_set

    def create_widgets(self):
        """创建界面组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部区域 - 文件选择和按钮
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=5)
        
        # 文件路径输入框和按钮在同一行
        path_frame = ttk.Frame(top_frame)
        path_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(path_frame, text="图像路径:").pack(side=tk.LEFT, padx=5)
        entry = ttk.Entry(path_frame, textvariable=self.image_path, width=50)
        entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 浏览按钮 - 放在输入框同一行
        browse_btn = ttk.Button(path_frame, text="选择文件", command=self.browse_file)
        browse_btn.pack(side=tk.LEFT, padx=5, pady=2)
        
        # 剪贴板按钮 - 放在输入框同一行
        clipboard_btn = ttk.Button(path_frame, text="读取剪贴板", command=self.read_clipboard)
        clipboard_btn.pack(side=tk.LEFT, padx=5, pady=2)
        
        # 模板选择区域
        template_frame = ttk.Frame(main_frame)
        template_frame.pack(fill=tk.X, pady=5)
        
        # 左侧 - 模板选择
        left_template_frame = ttk.Frame(template_frame)
        left_template_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(left_template_frame, text="选择模板集:").pack(side=tk.LEFT, padx=5)
        self.template_combo = ttk.Combobox(left_template_frame, textvariable=self.template_set, state="readonly", width=20)
        self.template_combo.pack(side=tk.LEFT, padx=5)
        
        # 添加创建模板按钮
        create_template_btn = ttk.Button(left_template_frame, text="创建模板", command=self.create_template)
        create_template_btn.pack(side=tk.LEFT, padx=5)
        
        # 右侧 - 匹配识别和查看图片按钮（放在模板选择同一行的右侧）
        right_template_frame = ttk.Frame(template_frame)
        right_template_frame.pack(side=tk.RIGHT)
        
        # 查看图片按钮
        view_btn = ttk.Button(right_template_frame, text="查看图片", command=self.view_image)
        view_btn.pack(side=tk.LEFT, padx=5, pady=2)
        
        # 匹配识别按钮
        self.process_btn = ttk.Button(right_template_frame, text="匹配识别", command=self.process_image)
        self.process_btn.pack(side=tk.LEFT, padx=5, pady=2)
        
        # 创建左右分栏布局
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 左侧区域 - 图像预览 (固定大小为480x300)
        left_frame = ttk.Frame(content_frame, width=480, height=300)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        left_frame.pack_propagate(False)  # 防止子组件改变frame大小
        
        preview_frame = ttk.LabelFrame(left_frame, text="图像预览")
        preview_frame.pack(fill=tk.BOTH, expand=True)
        
        self.preview_label = ttk.Label(preview_frame)
        self.preview_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 右侧区域 - 识别结果
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        result_frame = ttk.LabelFrame(right_frame, text="识别结果")
        result_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建文本框和滚动条的容器
        text_container = ttk.Frame(result_frame)
        text_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建水平滚动条
        h_scrollbar = ttk.Scrollbar(text_container, orient=tk.HORIZONTAL)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 创建垂直滚动条
        v_scrollbar = ttk.Scrollbar(text_container)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建文本框用于显示结果，禁用自动换行
        self.result_text = tk.Text(text_container, wrap=tk.NONE, height=10, 
                                  yscrollcommand=v_scrollbar.set,
                                  xscrollcommand=h_scrollbar.set)
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 配置滚动条与文本框的关联
        v_scrollbar.config(command=self.result_text.yview)
        h_scrollbar.config(command=self.result_text.xview)
    def load_preview(self, image_path):
        """加载并显示图像预览"""
        try:
            # 读取图像
            image = Image.open(image_path)
            
            # 计算缩放比例以适应预览区域
            preview_width = 460  # 留出一些边距
            preview_height = 280  # 留出一些边距
            ratio = min(preview_width/image.width, preview_height/image.height)
            new_width = int(image.width * ratio)
            new_height = int(image.height * ratio)
            
            # 调整图像大小
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            # 转换为PhotoImage对象
            photo = ImageTk.PhotoImage(image)
            # 更新预览标签
            self.preview_label.configure(image=photo)
            self.preview_label.image = photo  # 保持引用以防止垃圾回收
            
        except Exception as e:
            messagebox.showerror("错误", f"加载预览图像失败: {str(e)}")
            self.preview_label.configure(image='')
            self.preview_label.image = None

    def copy_to_clipboard(self, text):
        """复制文本到剪贴板（线程安全）"""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()  # 确保更新剪贴板
        except Exception as e:
            print(f"复制到剪贴板失败: {str(e)}")

    def run_processing(self, image_path):
        """在后台线程中运行图像处理"""
        try:
            # 获取选择的模板集
            template_set = self.template_set.get()
            
            # 创建日志文件，但暂不写入内容
            log_file = None
            
            # 步骤1: 分割纸牌
            self.update_status("步骤1/3: 分割纸牌...")
            # 使用numpy读取图像以支持中文路径
            image = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                raise Exception("无法读取图像")
            
            # 重定向print输出到GUI
            import sys
            original_stdout = sys.stdout
            
            class GuiOutput:
                def __init__(self, text_widget):
                    self.text_widget = text_widget
                def write(self, message):
                    self.text_widget.after(0, self._write_and_scroll, message)
                def _write_and_scroll(self, message):
                    self.text_widget.insert(tk.END, message)
                    self.text_widget.see(tk.END)  # 自动滚动到最新内容
                def flush(self):
                    pass
            sys.stdout = GuiOutput(self.result_text)
            
            try:
                # 步骤1: 分割纸牌
                splitter = CardSplitter()
                splitter.split_cards(image)
                self.update_result("✓ 纸牌分割完成，已保存到Single_Card_Images目录\n")
                
                # 如果选择了"自动"，根据单张纸牌尺寸自动选择模板集
                if template_set == "自动":
                    template_set = self.check_card_size_and_select_template()
                
                template_dir = os.path.join('Card_Rank_Templates', template_set)
                if not os.path.exists(template_dir):
                    raise Exception(f"模板目录不存在: {template_dir}")
                
                # 步骤2: 提取数字
                self.update_status("步骤2/3: 提取数字...")
                extract_numbers.process_cards()
                self.update_result("✓ 数字提取完成，已保存到Card_Rank_Images目录\n")
                
                # 步骤3: 识别数字并生成布局
                self.update_status("步骤3/3: 识别数字并生成布局...")
                
                # 在识别开始前创建日志文件
                log_file = open("Card_Match_Result.log", "w", encoding="utf-8")
                log_file.write("识别结果,文件名,点数,匹配度,匹配次数,用时,方法\n")
                
                # 处理所有卡片
                results = []
                start_time = time.time()
                input_dir = 'Card_Rank_Images'
                image_files = sorted([f for f in os.listdir(input_dir) if f.endswith('.png')])
                
                for filename in image_files:
                    image_path = os.path.join(input_dir, filename)
                    
                    # 使用match_card_rank函数进行识别，传入模板目录
                    number, confidence, match_count, process_time = match_numbers.match_card_rank(image_path, template_dir)
                    color_simple = 'r' if '_r.' in filename else 'b'
                    
                    # 记录结果
                    error_msg = "识别失败" if number is None else ""
                    log_line = match_numbers.create_log_line(filename, number, color_simple, confidence, match_count, process_time, error_msg)
                    log_file.write(log_line)
                    self.update_result(log_line.strip() + "\n")
                    
                    # 即使识别失败也添加到结果中，使用默认值
                    if number:
                        results.append({
                            'number': number, 
                            'color': color_simple, 
                            'filename': filename
                        })
                    else:
                        # 添加一个占位符结果，以便在布局中显示未识别的卡片
                        results.append({
                            'number': '?', 
                            'color': color_simple, 
                            'filename': filename
                        })
                
                # 格式化输出 - 修复缩进，将这部分代码移出循环
                if results:
                    # 使用新的函数生成布局
                    columns, red_first, black_first = match_numbers.results_to_columns(results)
                    layout_lines, is_valid, errors = match_numbers.format_columns_to_text(columns)
                    
                    # 显示在GUI中
                    self.update_result("\nFreecell Layout:\n")
                    for line in layout_lines:
                        self.update_result(line + "\n")
                    
                    # 写入日志文件
                    with open("Card_Match_Result.log", "a", encoding="utf-8") as log_file:
                        log_file.write("\n")
                        for line in layout_lines:
                            log_file.write(line + "\n")
                    
                    # 检查是否所有卡片都识别成功且通过完整性验证
                    all_recognized = all(result['number'] != '?' for result in results)
                    
                    # 仅当所有卡片都识别成功且通过完整性验证时才复制到剪贴板
                    if all_recognized and is_valid:
                        # 提取不包含验证信息的布局行
                        clipboard_lines = layout_lines[:-2] if is_valid else layout_lines[:-2-len(errors)]
                        
                        # 复制到剪贴板
                        clipboard_text = "\n".join(clipboard_lines)
                        self.root.after(0, lambda: self.copy_to_clipboard(clipboard_text))
                        self.update_result("\n布局已复制到剪贴板\n")
                    else:
                        self.update_result("\n布局未通过完整性验证，未复制到剪贴板\n")
                
                # 输出统计
                success_count = sum(1 for result in results if result['number'] != '?')
                total_time = int((time.time() - start_time) * 1000)
                summary = f"\n共识别成功 {success_count} 张卡牌，总用时 {total_time}ms"
                self.update_result(summary)
                
                # 确保日志文件仍然打开时才写入
                if log_file and not log_file.closed:
                    log_file.write(summary + "\n")
                else:
                    # 如果日志文件已关闭，重新打开并追加
                    with open("Card_Match_Result.log", "a", encoding="utf-8") as append_log:
                        append_log.write(summary + "\n")
            finally:
                sys.stdout = original_stdout
                # 确保日志文件存在且打开时才关闭
                if log_file and not log_file.closed:
                    log_file.close()  # 关闭日志文件
                
            self.update_status("处理完成")
        except Exception as e:
            self.update_result(f"\n错误: {str(e)}")
            self.update_status(f"处理失败: {str(e)}")
        finally:
            # 完成处理
            self.root.after(0, self.finish_processing)

    def update_status(self, message):
        """更新状态信息（线程安全）"""
        self.root.after(0, lambda: self.status_var.set(message))
    def update_result(self, message):
        """更新结果文本（线程安全）"""
        def update():
            self.result_text.insert(tk.END, message)
            self.result_text.see(tk.END)  # 自动滚动到最新内容
        self.root.after(0, update)
    def finish_processing(self):
        """完成处理"""
        self.processing = False
        self.process_btn.config(state=tk.NORMAL)
        
    def clear_image_directories(self):
        """清空图像处理目录"""
        dirs = ["Single_Card_Images", "Card_Rank_Images"]
        for dir_name in dirs:
            if os.path.exists(dir_name):
                for file in os.listdir(dir_name):
                    try:
                        os.remove(os.path.join(dir_name, file))
                    except Exception as e:
                        print(f"清除文件失败: {file}, 错误: {str(e)}")
            else:
                os.makedirs(dir_name, exist_ok=True)
                
    def save_current_image_as_layout(self):
        """将当前载入的图像保存为Freecell_Layout.png"""
        try:
            image_path = self.image_path.get()
            if image_path and os.path.exists(image_path):
                # 读取原始图像
                image = Image.open(image_path)
                # 保存为Freecell_Layout.png，覆盖已有文件
                layout_path = "Freecell_Layout.png"
                image.save(layout_path)
                self.update_result(f"已保存当前图像为 {layout_path}\n")
        except Exception as e:
            self.update_result(f"保存图像失败: {str(e)}\n")
    
    def process_image(self):
        """处理图像的主函数"""
        if self.processing:
            messagebox.showinfo("提示", "正在处理中，请稍候...")
            return
        
        image_path = self.image_path.get()
        if not image_path or not os.path.exists(image_path):
            messagebox.showinfo("提示", "请先选择有效的图像文件")
            return
            
        # 保存当前图像为Freecell_Layout.png
        self.save_current_image_as_layout()
            
        # 开始处理前先清空目录
        self.clear_image_directories()
        
        # 开始处理
        self.processing = True
        self.process_btn.config(state=tk.DISABLED)
        # 清空结果区域
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "开始处理图像...\n")
        # 在新线程中运行处理过程
        thread = threading.Thread(target=self.run_processing, args=(image_path,))
        thread.daemon = True
        thread.start()
    # 在 create_widgets 方法后添加 browse_file 方法
    def browse_file(self):
        """打开文件选择对话框"""
        try:
            filetypes = [
                ("图像文件", "*.png *.jpg *.jpeg *.bmp"),
                ("所有文件", "*.*")
            ]
            filename = filedialog.askopenfilename(title="选择FreeCell游戏截图", filetypes=filetypes)
            if filename:
                self.image_path.set(filename)
                self.load_preview(filename)
        except Exception as e:
            messagebox.showerror("错误", f"选择文件时出错: {str(e)}")
    def read_clipboard(self):
        """从剪贴板读取图像"""
        try:
            # 从剪贴板获取图像
            image = ImageGrab.grabclipboard()
            if image is None:
                messagebox.showerror("错误", "剪贴板中没有图像")
                return
            
            # 直接保存为Freecell_Layout.png
            layout_path = "Freecell_Layout.png"
            image.save(layout_path)
            
            # 设置路径并预览
            self.image_path.set(os.path.abspath(layout_path))
            self.load_preview(layout_path)
            self.status_var.set("已从剪贴板读取图像")
            
        except Exception as e:
            messagebox.showerror("错误", f"读取剪贴板失败: {str(e)}")
            self.status_var.set("读取剪贴板失败")
            
    def view_image(self):
        """查看当前图像"""
        image_path = self.image_path.get()
        if not image_path or not os.path.exists(image_path):
            messagebox.showinfo("提示", "请先选择有效的图像文件")
            return
        
        # 修改这里：传递self.root而不是self作为父窗口
        viewer = CardViewerWindow(self.root, image_path, self)

# 添加新的卡片查看器窗口类
class CardViewerWindow:
    def __init__(self, parent, image_path, app=None):
        self.parent = parent  # 这是Tkinter窗口对象
        self.app = app  # 这是FreecellOCRApp实例
        self.image_path = image_path
        
        # 创建新窗口
        self.window = tk.Toplevel(parent)
        self.window.title("纸牌查看器")
        self.window.geometry("1024x832")  # 设置窗口大小为1024x832
        self.window.resizable(True, True)  # 允许调整大小
        
        # 添加标记，用于跟踪是否有修改
        self.modified = False
        self.card_values = {}  # 存储卡片值，用于跟踪修改
        
        # 创建界面
        self.create_widgets()
        
        # 加载图像
        self.load_image()
        
        # 加载卡片
        self.load_cards()
        
        # 绑定窗口关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
                
    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 上方图像区域 (高度为400，宽度自适应)
        self.image_frame = ttk.Frame(main_frame, height=400)
        self.image_frame.pack(fill=tk.X, pady=(0, 10))
        self.image_frame.pack_propagate(False)  # 防止子组件改变frame大小
        
        # 创建内部框架用于居中显示图像
        self.image_center_frame = ttk.Frame(self.image_frame)
        self.image_center_frame.pack(expand=True)
        
        self.image_label = ttk.Label(self.image_center_frame)
        self.image_label.pack()
        
        # 下方卡片区域 (8列7行，占满剩余空间)
        self.cards_frame = ttk.Frame(main_frame)
        self.cards_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建8x7网格
        self.card_labels = []
        self.all_entries = []  # 存储所有文本框，用于导航
        
        for row in range(7):
            row_labels = []
            for col in range(8):
                # 跳过最后一行的后4个格子（第7行的第5-8列）
                if row == 6 and col >= 4:
                    row_labels.append(None)  # 添加None作为占位符
                    continue
                    
                frame = ttk.Frame(self.cards_frame, borderwidth=1, relief="solid")
                frame.grid(row=row, column=col, padx=2, pady=2, sticky="nsew")
                
                # 创建标签显示卡片
                card_label = ttk.Label(frame)
                card_label.pack(side=tk.LEFT, padx=2)
                
                # 创建文本框显示卡片标识，可直接编辑
                id_var = tk.StringVar(value=f"{col+1}{chr(65+row)}")
                id_entry = ttk.Entry(frame, textvariable=id_var, width=4, justify='center')
                id_entry.pack(side=tk.RIGHT, padx=2)
                
                # 将文本框添加到列表中，用于导航
                self.all_entries.append((row, col, id_entry))
                
                # 绑定文本变化事件
                id_var.trace_add("write", lambda name, index, mode, r=row, c=col, v=id_var: self.on_text_changed(r, c, v))

                # 绑定按键事件
                id_entry.bind("<Return>", lambda event, r=row, c=col: self.navigate_entries(event, r, c, "down"))
                id_entry.bind("<Tab>", lambda event, r=row, c=col: self.navigate_entries(event, r, c, "right"))
                id_entry.bind("<Shift-Return>", lambda event, r=row, c=col: self.navigate_entries(event, r, c, "up"))
                id_entry.bind("<Shift-Tab>", lambda event, r=row, c=col: self.navigate_entries(event, r, c, "left"))
                
                # 添加方向键绑定
                id_entry.bind("<Down>", lambda event, r=row, c=col: self.navigate_entries(event, r, c, "down"))
                id_entry.bind("<Right>", lambda event, r=row, c=col: self.navigate_entries(event, r, c, "right"))
                id_entry.bind("<Up>", lambda event, r=row, c=col: self.navigate_entries(event, r, c, "up"))
                id_entry.bind("<Left>", lambda event, r=row, c=col: self.navigate_entries(event, r, c, "left"))
                
                row_labels.append((card_label, id_entry, frame, id_var))
            self.card_labels.append(row_labels)
        
        # 设置列和行的权重，使其均匀分布
        for i in range(8):
            self.cards_frame.columnconfigure(i, weight=1)
        for i in range(7):
            self.cards_frame.rowconfigure(i, weight=1)
    
    def navigate_entries(self, event, current_row, current_col, direction):
        """在文本框之间导航
        
        Args:
            event: 按键事件
            current_row: 当前行
            current_col: 当前列
            direction: 导航方向 ("up", "down", "left", "right")
        """
        # 计算下一个位置
        next_row, next_col = current_row, current_col
        
        if direction == "down":
            next_row = (current_row + 1) % 7
            # 如果是最后一行的无效位置，调整到有效位置
            if next_row == 6 and next_col >= 4:
                next_col = 3  # 移动到最后一行的最后一个有效列
        elif direction == "up":
            next_row = (current_row - 1) % 7
            # 如果是最后一行的无效位置，调整到有效位置
            if next_row == 6 and next_col >= 4:
                next_col = 3  # 移动到最后一行的最后一个有效列
        elif direction == "right":
            next_col = (current_col + 1) % 8
            # 如果移动到下一行
            if next_col == 0:
                next_row = (current_row + 1) % 7
            # 如果是最后一行的无效位置，调整到下一个有效位置
            if next_row == 6 and next_col >= 4:
                next_row = 0
                next_col = 0  # 回到第一行第一列
        elif direction == "left":
            next_col = (current_col - 1) % 8
            # 如果移动到上一行
            if next_col == 7:
                next_row = (current_row - 1) % 7
            # 如果是最后一行的无效位置，调整到上一个有效位置
            if next_row == 6 and next_col >= 4:
                next_row = 6
                next_col = 3  # 移动到最后一行的最后一个有效列
        
        # 查找下一个文本框并设置焦点
        for row, col, entry in self.all_entries:
            if row == next_row and col == next_col:
                entry.focus_set()
                entry.select_range(0, tk.END)  # 选中所有文本
                break
        
        # 重要：返回"break"以阻止默认的Tab行为
        return "break"
    
    def on_text_changed(self, row, col, var):
        """文本框内容变化时的回调函数"""
        position_key = f"{row},{col}"
        if position_key in self.card_values:
            new_value = var.get().strip()
            if new_value != self.card_values[position_key]['value']:
                self.card_values[position_key]['value'] = new_value
                self.modified = True
    
    def load_cards(self):
        """加载并显示卡片图像"""
        card_dir = "Card_Rank_Images"
        if not os.path.exists(card_dir):
            messagebox.showinfo("提示", "Card_Rank_Images目录不存在")
            return
        
        # 清空所有卡片标签
        for row in self.card_labels:
            for cell in row:
                if cell:  # 检查是否为None
                    card_label, id_entry, frame, _ = cell
                    card_label.configure(image='')
                    card_label.image = None
        
        # 创建自定义样式
        style = ttk.Style()
        style.configure('red.TFrame', background='#ffcccc')  # 更鲜艳的红色背景
        style.configure('black.TFrame', background='#ccccff')  # 更鲜艳的蓝色背景
        
        # 加载卡片图像
        for filename in os.listdir(card_dir):
            if filename.endswith('.png'):
                try:
                    # 从文件名中提取位置信息 (例如: 34_r.png -> 列3, 行4)
                    match = re.match(r'(\d+)_([rb])\.png', filename)
                    if match:
                        col_row = match.group(1)
                        if len(col_row) == 2:
                            col = int(col_row[0]) - 1  # 列号从0开始
                            row = int(col_row[1]) - 1  # 行号从0开始
                            color_type = match.group(2)  # 获取颜色类型 (r或b)
                            
                            # 检查位置是否有效且不是被跳过的格子
                            if 0 <= col < 8 and 0 <= row < 7 and not (row == 6 and col >= 4):
                                # 加载图像
                                image_path = os.path.join(card_dir, filename)
                                image = Image.open(image_path)
                                
                                # 调整图像大小
                                image = image.resize((40, 40), Image.Resampling.LANCZOS)
                                
                                # 转换为PhotoImage对象
                                photo = ImageTk.PhotoImage(image)
                                
                                # 获取点数识别结果
                                card_value = self.get_card_value(filename)
                                
                                # 存储卡片值和文件名，用于跟踪修改
                                position_key = f"{row},{col}"
                                self.card_values[position_key] = {
                                    'value': card_value,
                                    'filename': filename,
                                    'color_type': color_type,
                                    'original_value': card_value  # 保存原始值用于比较
                                }
                                
                                # 更新卡片标签
                                cell = self.card_labels[row][col]
                                if cell:  # 检查是否为None
                                    card_label, id_entry, frame, id_var = cell
                                    card_label.configure(image=photo)
                                    card_label.image = photo  # 保持引用以防止垃圾回收
                                    
                                    # 更新文本框显示为点数识别结果
                                    id_var.set(card_value)
                                    
                                    # 设置背景颜色
                                    color = 'red' if color_type == 'r' else 'black'
                                    frame.configure(style=f'{color}.TFrame')
                except Exception as e:
                    print(f"加载卡片失败: {filename}, 错误: {str(e)}")
    
    def on_closing(self):
        """窗口关闭时的处理"""
        if self.modified:
            response = messagebox.askyesnocancel("保存修改", "识别结果已被修改，是否保存更改？")
            if response is None:  # 取消关闭
                return
            if response:  # 确认保存
                self.save_modified_results()
        
        self.window.destroy()
    
    def save_modified_results(self):
        """保存修改后的结果"""
        try:
            # 准备修改后的结果
            results = []
            
            # 遍历所有文本框，获取用户输入的值
            for row, col, entry in self.all_entries:
                position_key = f"{row},{col}"
                
                # 获取用户输入的值
                card_value = entry.get().strip()
                
                # 如果该位置有对应的卡片信息
                if position_key in self.card_values:
                    card_info = self.card_values[position_key]
                    
                    # 确保卡片值格式正确（例如：Ah, 2c, 10d 等）
                    # 标准化卡片值格式
                    if len(card_value) >= 1:
                        # 提取数字/字母部分和花色部分
                        if len(card_value) == 1:
                            # 如果只有一个字符，假设它是数字/字母部分，使用原始颜色
                            rank = card_value.upper()
                            suit = 'H' if card_info['color_type'] == 'r' else 'S'  # 默认红桃或黑桃
                        else:
                            # 否则，假设最后一个字符是花色
                            rank = card_value[:-1].upper()
                            suit = card_value[-1].upper()  # 确保花色是大写
                        
                        # 标准化花色（确保是H, D, C, S中的一个）
                        if suit not in ['H', 'D', 'C', 'S']:
                            if card_info['color_type'] == 'r':
                                suit = 'H'  # 默认红桃
                            else:
                                suit = 'S'  # 默认黑桃
                        
                        # 重新组合卡片值
                        card_value = rank + suit
                    
                    results.append({
                        'number': rank,  # 只保存点数部分
                        'color': 'r' if suit in ['H', 'D'] else 'b',  # 根据花色确定颜色
                        'filename': card_info['filename'],
                        'position': (row, col)  # 添加位置信息用于排序
                    })
            
            # 按照位置排序结果，确保卡片顺序正确
            # 先按行排序，再按列排序
            results.sort(key=lambda x: (x['position'][0], x['position'][1]))
            
            # 移除临时的位置信息
            for result in results:
                result.pop('position', None)
            
            # 使用新的函数生成布局
            columns, red_first, black_first = match_numbers.results_to_columns(results)
            layout_lines, is_valid, errors = match_numbers.format_columns_to_text(columns)
            
            # 写入日志文件
            with open("Card_Match_Result.log", "a", encoding="utf-8") as log_file:
                log_file.write("\n\n# 手动修改后的结果\n")
                for line in layout_lines:
                    log_file.write(line + "\n")
            
            # 检查是否所有卡片都识别成功且通过完整性验证
            all_recognized = all(result['number'] != '?' for result in results)
            
            # 在主界面的结果文本框中显示修改后的布局
            try:
                # 使用self.app访问主应用程序实例
                if self.app and hasattr(self.app, 'result_text'):
                    # 添加分隔行
                    self.app.result_text.insert(tk.END, "\n\n# 手动修改后的结果\n")
                    # 添加每一行布局
                    for line in layout_lines:
                        self.app.result_text.insert(tk.END, line + "\n")
                    # 滚动到最新内容
                    self.app.result_text.see(tk.END)
                else:
                    print("未找到主界面的result_text控件，仅保存到日志文件")
            except Exception as e:
                print(f"向主界面添加结果时出错: {str(e)}")

            # 仅当所有卡片识别成功且通过完整性验证时才复制到剪贴板
            if all_recognized and is_valid:
                # 提取不包含验证信息的布局行
                clipboard_lines = layout_lines[:-2] if is_valid else layout_lines[:-2-len(errors)]
                
                # 复制到剪贴板
                clipboard_text = "\n".join(clipboard_lines)
                self.window.clipboard_clear()
                self.window.clipboard_append(clipboard_text)
                self.window.update()
                messagebox.showinfo("保存成功", "修改后的布局已保存并复制到剪贴板")
            else:
                messagebox.showinfo("保存成功", "修改后的布局已保存，但未通过完整性验证，未复制到剪贴板")

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"保存修改后的结果失败: {str(e)}\n{error_details}")
            messagebox.showerror("保存失败", f"保存修改后的结果失败: {str(e)}")

    def load_image(self):
            """加载并显示原始图像"""
            try:
                # 读取图像
                image = Image.open(self.image_path)
                
                # 计算缩放比例以适应预览区域（保持原比例，高度为400）
                max_height = 400
                ratio = max_height / image.height
                new_width = int(image.width * ratio)
                new_height = max_height
                
                # 调整图像大小
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 转换为PhotoImage对象
                photo = ImageTk.PhotoImage(image)
                
                # 更新图像标签
                self.image_label.configure(image=photo)
                self.image_label.image = photo  # 保持引用以防止垃圾回收
                
            except Exception as e:
                messagebox.showerror("错误", f"加载图像失败: {str(e)}")
    
    def get_card_value(self, filename):
        """从日志文件中获取卡片的识别结果"""
        try:
            log_path = "Card_Match_Result.log"
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if filename in line:
                            # 提取识别结果 (格式: "识别成功: 86_b.png , Ab , [93.5%] , [9ms]")
                            parts = line.split(',')
                            if len(parts) > 1:
                                # 从第二部分提取实际的识别结果
                                result = parts[1].strip()
                                return result  # 返回识别结果 (如 "Ab")
        
            # 如果没有找到识别结果，从文件名中提取位置作为默认值
            match = re.match(r'(\d+)_([rb])\.png', filename)
            if match:
                col_row = match.group(1)
                if len(col_row) == 2:
                    col = col_row[0]
                    row = col_row[1]
                    return f"{col}{row}"
                
            return "?"  # 默认值
        except Exception as e:
            print(f"获取卡片值失败: {filename}, 错误: {str(e)}")
            return "?"

def main():
    """程序入口函数"""
    root = tk.Tk()
    app = FreecellOCRApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
    
