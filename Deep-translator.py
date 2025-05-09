# 依赖安装说明（不要保留可执行代码）
# 请先在终端运行以下命令：
# pip install openai pillow pytesseract
# 安装 Tesseract OCR（参考之前的指南）

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image
import pytesseract
from openai import OpenAI
import threading
import os
import sys

# 配置 Tesseract 路径（动态适配打包环境）
if getattr(sys, 'frozen', False):
    # 打包后的路径
    tesseract_path = os.path.join(sys._MEIPASS, 'Tesseract-OCR', 'tesseract.exe')
else:
    # 开发环境路径
    tesseract_path = r'D:\Tesseract\tesseract.exe'

pytesseract.pytesseract.tesseract_cmd = tesseract_path

class TranslationApp:
    def __init__(self, root):
        self.root = root
        self.custom_terms = []
        self.client = None
        self.create_widgets()

    def create_widgets(self):
        # 顶部控制栏
        top_frame = ttk.Frame(self.root)
        top_frame.pack(pady=10, fill=tk.X)

        # 输入类型选择
        self.input_type = tk.StringVar(value="text")
        ttk.Radiobutton(top_frame, text="文本输入", variable=self.input_type, value="text", command=self.toggle_input).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(top_frame, text="图片输入", variable=self.input_type, value="image", command=self.toggle_input).pack(side=tk.LEFT, padx=5)

        # 目标语言选择
        ttk.Label(top_frame, text="目标语言:").pack(side=tk.LEFT, padx=5)
        self.lang_var = tk.StringVar()
        self.lang_combo = ttk.Combobox(top_frame, textvariable=self.lang_var, values=["中文", "英文"], width=8)
        self.lang_combo.set("中文")
        self.lang_combo.pack(side=tk.LEFT, padx=5)
        
        # 自定义术语
        ttk.Button(top_frame, text="上传术语文件", command=self.load_terms).pack(side=tk.LEFT, padx=5)
        self.terms_label = ttk.Label(top_frame, text="已加载0条术语")
        self.terms_label.pack(side=tk.LEFT, padx=5)

        # API密钥
        ttk.Label(top_frame, text="API密钥:").pack(side=tk.LEFT, padx=5)
        self.api_key_entry = ttk.Entry(top_frame, show="*", width=25)
        self.api_key_entry.pack(side=tk.LEFT, padx=5)

        # 主内容区域
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 输入区
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        ttk.Label(input_frame, text="输入内容").pack()
        self.text_input = tk.Text(input_frame, height=25, width=50, wrap=tk.WORD)
        self.text_input.pack(fill=tk.BOTH, expand=True)
        
        # 图片输入组件
        self.img_frame = ttk.Frame(input_frame)
        self.image_path = tk.StringVar()
        ttk.Label(self.img_frame, text="图片路径:").pack(side=tk.LEFT)
        ttk.Entry(self.img_frame, textvariable=self.image_path, width=40, state='readonly').pack(side=tk.LEFT)
        ttk.Button(self.img_frame, text="浏览", command=self.select_image).pack(side=tk.LEFT)

        # 输出区
        output_frame = ttk.Frame(main_frame)
        output_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        ttk.Label(output_frame, text="翻译结果").pack()
        self.output_text = tk.Text(output_frame, height=25, width=50, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True)

        # 翻译按钮
        self.translate_btn = ttk.Button(self.root, text="开始翻译", command=self.start_translation)
        self.translate_btn.pack(pady=10)

        self.toggle_input()

    def toggle_input(self):
        if self.input_type.get() == "text":
            self.text_input.pack()
            self.img_frame.pack_forget()
        else:
            self.text_input.pack_forget()
            self.img_frame.pack()

    def select_image(self):
        path = filedialog.askopenfilename(filetypes=[("图片文件", "*.png *.jpg *.jpeg")])
        if path:
            self.image_path.set(path)

    def load_terms(self):
        path = filedialog.askopenfilename(filetypes=[("文本文件", "*.txt")])
        if path:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.custom_terms = []
                    for line in f:
                        line = line.strip()
                        self.custom_terms.append(line)
                    self.terms_label.config(text=f"已加载{len(self.custom_terms)}条自定义术语")
            except Exception as e:
                messagebox.showerror("错误", f"加载术语文件失败: {str(e)}")

    def start_translation(self):
        self.translate_btn.config(state=tk.DISABLED)
        threading.Thread(target=self.do_translation).start()
            
    # 其他方法保持不变，直到 do_translation 方法...

    def do_translation(self):
        try:
            # 获取输入文本（保持不变）
            if self.input_type.get() == "text":
                text = self.text_input.get("1.0", tk.END).strip()
            else:
                if not self.image_path.get():
                    messagebox.showwarning("警告", "请先选择图片文件")
                    return
                text = pytesseract.image_to_string(Image.open(self.image_path.get()))

            # 获取API密钥
            api_key = self.api_key_entry.get().strip()
            if not api_key:
                messagebox.showwarning("警告", "请输入API密钥")
                return

            # 构建系统提示词（新增术语处理逻辑）
            system_prompt = """你是一个专业翻译家，请遵守以下规则：
1. 自动识别输入语言并翻译为指定目标语言
2. 严格应用以下术语替换规则：\n"""
            
            # 添加术语替换说明
            if self.custom_terms:
                system_prompt += "在翻译时若遇到以下词或词组对中的左侧或右侧，请直接按照对应关系替换：\n"
                for line in self.custom_terms:
                    system_prompt += f"- '{line}'\n"
            
            system_prompt += """3. 翻译标准：
- 信：忠实原文内容
- 达：译文通顺自然
- 雅：语言优美地道
4. 目标语言：""" + ("中文" if self.lang_var.get() == "中文" else "英文")

            # 初始化客户端
            self.client = OpenAI(
                base_url="https://api.deepseek.com/",
                api_key=api_key
            )

            # API调用
            completion = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ]
            )

            translated = completion.choices[0].message.content
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(tk.END, translated)

        except Exception as e:
            messagebox.showerror("错误", f"翻译失败: {str(e)}")
        finally:
            self.root.after(0, lambda: self.translate_btn.config(state=tk.NORMAL))

# 其他方法保持不变...

if __name__ == "__main__":
    root = tk.Tk()
    root.title("智能翻译工具")
    root.geometry("1000x600")
    app = TranslationApp(root)
    root.mainloop()