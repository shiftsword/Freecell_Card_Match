import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import cv2
import numpy as np
import threading
import time
from PIL import Image, ImageTk, ImageGrab

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
                
        except Exception as e:
            messagebox.showerror("错误", f"启动模板创建工具失败: {str(e)}")
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
            self.template_set.set("set_1")  # 默认设置为set_1
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
        
        if not template_sets:
            self.template_set.set("set_1")  # 默认设置为set_1
        else:
            # 默认选择最新的模板集
            template_sets.sort()
            self.template_set.set(template_sets[-1])
            # 更新下拉菜单
            self.template_combo['values'] = template_sets
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
        
        # 创建文本框用于显示结果
        self.result_text = tk.Text(result_frame, wrap=tk.WORD, height=10)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(result_frame, command=self.result_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=scrollbar.set)
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
    def run_processing(self, image_path):
        """在后台线程中运行图像处理"""
        try:
            # 获取选择的模板集
            template_set = self.template_set.get()
            if template_set == "无可用模板":
                raise Exception("请先创建模板集")
            
            template_dir = os.path.join('Card_Rank_Templates', template_set)
            if not os.path.exists(template_dir):
                raise Exception(f"模板目录不存在: {template_dir}")
            
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
                splitter = CardSplitter()
                splitter.split_cards(image)
                self.update_result("✓ 纸牌分割完成，已保存到Single_Card_Images目录\n")
                
                # 步骤2: 提取数字
                self.update_status("步骤2/3: 提取数字...")
                extract_numbers.process_cards()
                self.update_result("✓ 数字提取完成，已保存到Card_Rank_Images目录\n")
                
                # 步骤3: 识别数字并生成布局
                self.update_status("步骤3/3: 识别数字并生成布局...")
                
                # 在识别开始前创建日志文件
                log_file = open("Card_Match_Result.log", "w", encoding="utf-8")
                
                # 使用选定的模板集进行识别
                template_manager = match_numbers.TemplateManager(template_dir)
                matcher = match_numbers.RankMatcher(template_manager)
                
                # 处理所有卡片
                results = []
                input_dir = 'Card_Rank_Images'
                image_files = sorted([f for f in os.listdir(input_dir) if f.endswith('.png')])
                for filename in image_files:
                    image_path = os.path.join(input_dir, filename)
                    color = '_r' if '_r.' in filename else '_b'
                    # 读取图像
                    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
                    if image is None:
                        continue
                    # 执行匹配
                    rank, confidence, _ = matcher.match_rank(image, color)
                    if rank:
                        results.append({
                            'number': rank, 
                            'color': color.replace('_', ''), 
                            'filename': filename
                        })
                        # 显示在GUI中
                        self.update_result(f"识别: {filename} -> {rank}{color}\n")
                        # 写入日志文件
                        log_file.write(f"识别: {filename} -> {rank}{color}\n")
                # 格式化输出 - 注意这里的缩进修正，应该在所有卡片处理完成后执行
                if results:
                    # 使用match_numbers.format_freecell_layout生成布局
                    # 传递self.root作为参数，以便使用主应用程序的Tkinter实例操作剪贴板
                    layout = match_numbers.format_freecell_layout(results, self.root)
                    
                    # 显示在GUI中
                    self.update_result("\nFreecell Layout:\n")
                    for line in layout:
                        self.update_result(line + "\n")
                    
                    # 写入日志文件
                    log_file.write("\nFreecell Layout:\n")
                    for line in layout:
                        log_file.write(line + "\n")
                        
                # 不再需要重复复制到剪贴板，因为format_freecell_layout已经做了
                # 移除以下代码:
                # self.root.clipboard_clear()
                # self.root.clipboard_append(layout_text)
                # self.root.update()
                # 不再需要重复输出复制成功信息，因为format_freecell_layout已经输出了
                # 移除以下代码:
                # self.update_result("\n布局已自动复制到剪贴板\n")
                # log_file.write("\n布局已自动复制到剪贴板\n")
                    
            finally:
                sys.stdout = original_stdout
                if log_file:
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
        
    def process_image(self):
        """处理图像的主函数"""
        if self.processing:
            messagebox.showinfo("提示", "正在处理中，请稍候...")
            return
        
        image_path = self.image_path.get()
        if not image_path or not os.path.exists(image_path):
            messagebox.showinfo("提示", "请先选择有效的图像文件")
            return
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
            
            # 保存为临时文件
            temp_path = "clipboard.png"
            image.save(temp_path)
            
            # 设置路径并预览
            self.image_path.set(os.path.abspath(temp_path))
            self.load_preview(temp_path)
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
        
        # 使用系统默认程序打开图像
        try:
            os.startfile(image_path)  # Windows
        except:
            try:
                import subprocess
                subprocess.call(["xdg-open", image_path])  # Linux
            except:
                try:
                    subprocess.call(["open", image_path])  # macOS
                except:
                    messagebox.showerror("错误", "无法打开图像文件")
def main():
    root = tk.Tk()
    app = FreecellOCRApp(root)
    root.mainloop()
if __name__ == "__main__":
        main()