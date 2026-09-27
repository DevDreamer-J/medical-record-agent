"""
语音病历生成 Agent - 图形界面（Tkinter + tkinterdnd2）
依赖：tkinterdnd2
安装：pip install tkinterdnd2
运行：python gui.py
"""
import os
import json
import shutil
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

from tkinterdnd2 import DND_FILES, TkinterDnD

from config.settings import Settings
from core.pipeline import MedicalRecordPipeline
from audio.preprocessor import AudioPreprocessor
from utils.logger import get_logger

logger = get_logger(__name__)

AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".wma", ".amr", ".opus"}
HISTORY_FILE = os.path.join("data", "history.json")
OUTPUT_DIR = os.path.join("data", "output")


class MedicalRecordApp(TkinterDnD.Tk):
    """语音病历生成 GUI"""

    def __init__(self):
        super().__init__()
        self.title("语音病历生成 Agent")
        self.geometry("860x680")
        self.resizable(False, False)

        # 状态
        self.audio_path = None
        self.output_path = None
        self.pipeline = None
        self.history = self._load_history()

        self._build_ui()
        self._refresh_history()

    # ===================== UI 构建 =====================
    def _build_ui(self):
        # 标题
        tk.Label(self, text="语音病历生成 Agent", font=("微软雅黑", 20, "bold")).pack(pady=(15, 8))

        # ===== 上半部分：输入与操作 =====
        top_frame = tk.Frame(self)
        top_frame.pack(fill="x", padx=20, pady=5)

        # 拖拽区域
        self.drop_frame = tk.Frame(top_frame, bg="#e3f2fd", height=110,
                                    highlightbackground="#90caf9", highlightthickness=2)
        self.drop_frame.pack(fill="x")
        self.drop_frame.pack_propagate(False)

        self.drop_label = tk.Label(
            self.drop_frame,
            text="📂  将音频文件拖拽到此处\n（支持 wav / mp3 / m4a / aac / flac / ogg 等）",
            font=("微软雅黑", 13), bg="#e3f2fd", fg="#1565c0",
        )
        self.drop_label.pack(expand=True)

        for w in (self.drop_frame, self.drop_label):
            w.drop_target_register(DND_FILES)
            w.dnd_bind("<<Drop>>", self._on_drop)

        # 文件信息行
        info_frame = tk.Frame(top_frame)
        info_frame.pack(fill="x", pady=(8, 0))

        self.file_label = tk.Label(info_frame, text="未选择文件", font=("微软雅黑", 11),
                                    fg="#666", anchor="w")
        self.file_label.pack(side="left")

        # 按钮行
        btn_frame = tk.Frame(top_frame)
        btn_frame.pack(fill="x", pady=8)

        self.confirm_btn = tk.Button(
            btn_frame, text="确认生成病历", font=("微软雅黑", 12, "bold"),
            bg="#1976d2", fg="white", width=16, height=2,
            relief="flat", cursor="hand2", state="disabled",
            command=self._on_confirm,
        )
        self.confirm_btn.pack(side="left", padx=(0, 10))

        self.save_as_btn = tk.Button(
            btn_frame, text="💾 另存为", font=("微软雅黑", 11),
            bg="#43a047", fg="white", width=12, height=2,
            relief="flat", cursor="hand2", state="disabled",
            command=self._on_save_as,
        )
        self.save_as_btn.pack(side="left", padx=(0, 10))

        self.open_word_btn = tk.Button(
            btn_frame, text="📄 打开 Word", font=("微软雅黑", 11),
            bg="#fb8c00", fg="white", width=12, height=2,
            relief="flat", cursor="hand2", state="disabled",
            command=self._open_word,
        )
        self.open_word_btn.pack(side="left")

        # 进度条
        self.progress = ttk.Progressbar(self, length=820, mode="determinate")
        self.progress.pack(pady=5)

        self.status_label = tk.Label(self, text="", font=("微软雅黑", 10), fg="#666")
        self.status_label.pack()

        # 结果展示
        result_frame = tk.LabelFrame(self, text="处理结果", font=("微软雅黑", 10, "bold"))
        result_frame.pack(fill="both", expand=True, padx=20, pady=8)

        self.result_text = tk.Text(result_frame, font=("微软雅黑", 10), wrap="word",
                                    height=8, state="disabled", bg="#fafafa")
        self.result_text.pack(fill="both", expand=True, padx=5, pady=5)

        # ===== 下半部分：历史记录 =====
        hist_frame = tk.LabelFrame(self, text="历史处理记录", font=("微软雅黑", 10, "bold"))
        hist_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        # 历史表格
        columns = ("time", "audio", "duration", "status")
        self.history_tree = ttk.Treeview(hist_frame, columns=columns, show="headings", height=6)
        self.history_tree.heading("time", text="处理时间")
        self.history_tree.heading("audio", text="音频文件")
        self.history_tree.heading("duration", text="音频长度")
        self.history_tree.heading("status", text="状态")

        self.history_tree.column("time", width=160, anchor="center")
        self.history_tree.column("audio", width=300, anchor="w")
        self.history_tree.column("duration", width=100, anchor="center")
        self.history_tree.column("status", width=80, anchor="center")

        self.history_tree.pack(fill="both", expand=True, padx=5, pady=5)

    # ===================== 拖拽 =====================
    def _on_drop(self, event):
        paths = self._parse_drop_paths(event.data)
        if not paths:
            return
        path = paths[0]
        ext = os.path.splitext(path)[1].lower()
        if ext not in AUDIO_EXTENSIONS:
            messagebox.showwarning("格式不支持", f"不支持的格式: {ext}")
            return
        self.audio_path = path
        self.file_label.config(text=f"已选择: {os.path.basename(path)}", fg="#1976d2")
        self.drop_label.config(text=f"✅  {os.path.basename(path)}", fg="#2e7d32")
        self.confirm_btn.config(state="normal")

    @staticmethod
    def _parse_drop_paths(data: str):
        paths, buf, in_brace = [], "", False
        for ch in data:
            if ch == "{":
                in_brace = True
            elif ch == "}":
                in_brace = False
                if buf:
                    paths.append(buf)
                    buf = ""
            elif ch == " " and not in_brace:
                if buf:
                    paths.append(buf)
                    buf = ""
            else:
                buf += ch
        if buf:
            paths.append(buf)
        return paths

    # ===================== 处理流程 =====================
    def _on_confirm(self):
        if not self.audio_path:
            return
        for btn in (self.confirm_btn, self.save_as_btn, self.open_word_btn):
            btn.config(state="disabled")
        self.output_path = None
        self._set_result("")
        threading.Thread(target=self._run_pipeline, daemon=True).start()

    def _run_pipeline(self):
        start_time = datetime.now()
        audio_name = os.path.basename(self.audio_path)
        duration_str = "未知"
        try:
            self._update_status("加载配置...")
            config = Settings.load_from_env()
            if not config.XUNFEI_APPID or config.XUNFEI_APPID == "xxxxx":
                raise Exception("请在 .env 中配置讯飞 ASR 凭证")
            if not config.LLM_API_KEY:
                raise Exception("请在 .env 中配置 LLM API Key")

            if self.pipeline is None:
                self.pipeline = MedicalRecordPipeline(config)

            # 获取音频时长
            try:
                pre = AudioPreprocessor()
                dur = pre.get_duration(self.audio_path)
                duration_str = f"{dur:.1f}秒" if dur > 0 else "未知"
            except Exception:
                pass

            self._update_progress(0.15, "步骤 1/4：音频预处理...")
            self._update_progress(0.40, "步骤 2/4：语音识别中...")
            self._update_progress(0.70, "步骤 3/4：大模型结构化...")
            self._update_progress(0.90, "步骤 4/4：生成 Word 文档...")

            # 确保输出到 data/output
            config.OUTPUT_DIR = OUTPUT_DIR
            self.pipeline.word_generator.output_dir = OUTPUT_DIR
            self.output_path = self.pipeline.run(self.audio_path)

            self._update_progress(1.0, "✅ 处理完成！")
            self._set_result(self._build_summary())
            self._save_as_btn_enable()
            self._add_history(start_time, audio_name, duration_str, "成功")

        except Exception as e:
            logger.error(f"处理失败: {e}")
            self._update_progress(0, "❌ 处理失败")
            self._set_result(f"处理失败：\n{e}")
            self._add_history(start_time, audio_name, duration_str, "失败")
            messagebox.showerror("处理失败", str(e))
        finally:
            self.confirm_btn.config(state="normal")

    def _build_summary(self):
        run_dir = os.path.dirname(self.output_path) if self.output_path else ""
        t_path = os.path.join(run_dir, "transcript.txt")
        j_path = os.path.join(run_dir, "structured.json")
        summary = f"✅ 病历已生成\n保存路径: {self.output_path}\n\n"
        if os.path.exists(t_path):
            with open(t_path, "r", encoding="utf-8") as f:
                summary += f"【转写文本】\n{f.read()}\n\n"
        if os.path.exists(j_path):
            with open(j_path, "r", encoding="utf-8") as f:
                record = json.load(f)
            summary += "【结构化结果】\n"
            for k, v in record.items():
                summary += f"  {k}: {v}\n"
        return summary

    # ===================== 另存为 / 打开 =====================
    def _save_as_btn_enable(self):
        if self.output_path and os.path.exists(self.output_path):
            self.save_as_btn.config(state="normal")
            self.open_word_btn.config(state="normal")

    def _on_save_as(self):
        if not self.output_path or not os.path.exists(self.output_path):
            messagebox.showinfo("提示", "暂无 Word 文档可保存")
            return
        default_name = os.path.basename(self.output_path)
        dest = filedialog.asksaveasfilename(
            title="另存为",
            initialfile=default_name,
            defaultextension=".docx",
            filetypes=[("Word 文档", "*.docx"), ("所有文件", "*.*")],
        )
        if dest:
            try:
                shutil.copy2(self.output_path, dest)
                messagebox.showinfo("成功", f"已保存到:\n{dest}")
            except Exception as e:
                messagebox.showerror("保存失败", str(e))

    def _open_word(self):
        if self.output_path and os.path.exists(self.output_path):
            os.startfile(self.output_path)

    # ===================== 历史记录 =====================
    def _load_history(self):
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def _save_history(self):
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.history, f, ensure_ascii=False, indent=2)

    def _add_history(self, start_time, audio_name, duration, status):
        self.history.insert(0, {
            "time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "audio": audio_name,
            "duration": duration,
            "status": status,
        })
        # 只保留最近 100 条
        self.history = self.history[:100]
        self._save_history()
        self._refresh_history()

    def _refresh_history(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for rec in self.history:
            self.history_tree.insert("", "end", values=(
                rec.get("time", ""),
                rec.get("audio", ""),
                rec.get("duration", ""),
                rec.get("status", ""),
            ))

    # ===================== 线程安全 UI 更新 =====================
    def _update_progress(self, value, status=""):
        def _do():
            self.progress["value"] = value * 100
            self.status_label.config(text=status)
        self.after(0, _do)

    def _update_status(self, text):
        self.after(0, lambda: self.status_label.config(text=text))

    def _set_result(self, text):
        def _do():
            self.result_text.config(state="normal")
            self.result_text.delete("1.0", "end")
            self.result_text.insert("end", text)
            self.result_text.config(state="disabled")
        self.after(0, _do)


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    app = MedicalRecordApp()
    app.mainloop()
