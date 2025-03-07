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
import recognize_numbers

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
        
        # 创建界面组件
        self.create_widgets()
        
        # 检查必要的目录
        self.check_directories()
    
    def check_directories(self):
        """检查并创建必要的目录"""
        # 清空并重建目录
        dirs = ["cards", "output"]
        for dir_name in dirs:
            if os.path.exists(dir_name):
                for file in os.listdir(dir_name):
                    os.remove(os.path.join(dir_name, file))
            os.makedirs(dir_name, exist_ok=True)
    
    def create_widgets(self):
        """创建界面组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 顶部区域 - 文件选择和按钮
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=5)
        
        # 文件路径输入框
        ttk.Label(top_frame, text="图像路径:").pack(side=tk.LEFT, padx=5)
        entry = ttk.Entry(top_frame, textvariable=self.image_path, width=50)
        entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 浏览按钮
        browse_btn = ttk.Button(top_frame, text="选择文件", command=self.browse_file)
        browse_btn.pack(side=tk.LEFT, padx=5)
        
        # 剪贴板按钮
        clipboard_btn = ttk.Button(top_frame, text="读取剪贴板", command=self.read_clipboard)
        clipboard_btn.pack(side=tk.LEFT, padx=5)
        
        # 中间区域 - 图像预览
        preview_frame = ttk.LabelFrame(main_frame, text="图像预览")
        preview_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.preview_label = ttk.Label(preview_frame)
        self.preview_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 底部区域 - 处理按钮和状态
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X, pady=5)
        
        # 处理按钮
        self.process_btn = ttk.Button(bottom_frame, text="OCR识别", command=self.process_image)
        self.process_btn.pack(side=tk.LEFT, padx=5)
        
        # 查看图片按钮
        view_btn = ttk.Button(bottom_frame, text="查看图片", command=self.view_image)
        view_btn.pack(side=tk.LEFT, padx=5)
        
        # 状态标签
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(status_frame, text="状态:").pack(side=tk.LEFT, padx=5)
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=5)
        
        # 进度条
        self.progress = ttk.Progressbar(status_frame, orient=tk.HORIZONTAL, length=200, mode='indeterminate')
        self.progress.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # 结果区域
        result_frame = ttk.LabelFrame(main_frame, text="识别结果")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 创建文本框用于显示结果
        self.result_text = tk.Text(result_frame, wrap=tk.WORD, height=10)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.result_text, command=self.result_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=scrollbar.set)
    
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
        
    def load_preview(self, image_path):
        """加载并显示图像预览"""
        try:
            # 读取图像
            image = Image.open(image_path)
            
            # 计算缩放比例以适应预览区域
            preview_width = 800
            preview_height = 600
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
                self.update_result("✓ 纸牌分割完成，已保存到cards目录\n")
                
                # 步骤2: 提取数字
                self.update_status("步骤2/3: 提取数字...")
                extract_numbers.process_cards()
                self.update_result("✓ 数字提取完成，已保存到output目录\n")
                
                # 步骤3: 识别数字并生成布局
                self.update_status("步骤3/3: 识别数字并生成布局...")
                results = recognize_numbers.process_all_cards()
            finally:
                sys.stdout = original_stdout
            
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
        self.progress.stop()
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
        self.status_var.set("处理中...")
        self.progress.start(10)
        self.process_btn.config(state=tk.DISABLED)
        
        # 清空结果区域
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, "开始处理图像...\n")
        
        # 在新线程中运行处理过程
        thread = threading.Thread(target=self.run_processing, args=(image_path,))
        thread.daemon = True
        thread.start()

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