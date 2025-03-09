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
                
                # 在run_processing方法中，修改调用match_card_rank的部分
                # 使用选定的模板集进行识别
                template_manager = match_numbers.TemplateManager(template_dir)
                matcher = match_numbers.RankMatcher(template_manager)
                
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
                
                # 格式化输出
                if results:
                    # 使用match_numbers.format_freecell_layout生成布局
                    layout = match_numbers.format_freecell_layout(results, None)  # 先不传入root，避免自动复制到剪贴板
                    
                    # 显示在GUI中
                    self.update_result("\nFreecell Layout:\n")
                    for line in layout:
                        self.update_result(line + "\n")
                    
                    # 写入日志文件
                    log_file.write("\n")
                    for line in layout:
                        log_file.write(line + "\n")
                    
                    # 检查是否所有卡片都识别成功且通过完整性验证
                    all_recognized = all(result['number'] != '?' for result in results)
                    # 检查布局中是否包含验证成功的信息
                    validation_passed = any("牌组完整且合法" in line for line in layout)
                    
                    # 仅当所有卡片识别成功且通过完整性验证时才复制到剪贴板
                    if all_recognized and validation_passed:
                        # 提取不包含验证信息的布局行
                        clipboard_lines = []
                        for line in layout:
                            if not line.startswith("# 牌组"):
                                clipboard_lines.append(line)
                        
                        # 复制到剪贴板
                        clipboard_text = "\n".join(clipboard_lines)
                        self.root.clipboard_clear()
                        self.root.clipboard_append(clipboard_text)
                        self.root.update()
                        self.update_result("\n布局已自动复制到剪贴板\n")
                        log_file.write("\n布局已自动复制到剪贴板\n")
                    # 移除未复制到剪贴板时的提示和记录
                
                # 在run_processing方法中，修改统计部分
                # 输出统计
                success_count = sum(1 for result in results if result['number'] != '?')
                total_time = int((time.time() - start_time) * 1000)
                summary = f"\n共识别成功 {success_count} 张卡牌，总用时 {total_time}ms"
                self.update_result(summary)
                log_file.write(summary + "\n")
                    
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
    
