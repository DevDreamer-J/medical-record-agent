# 语音病历生成 Agent

> 一款基于语音识别与大模型的门诊病历自动生成工具，拖拽音频即可生成结构化 Word 病历。

---

## 项目简介

本项目实现了一条完整的"录音 → 文字 → 结构化病历 → Word 文档"自动化流水线，旨在帮助医生快速将医患对话录音转化为规范的门诊病历，减少文书工作负担。

核心流程：

```
音频文件 → 格式预处理 → 讯飞语音识别(ASR) → 阿里云百炼大模型(LLM)结构化 → Word 病历
```

---

## 功能特性

- 🎙️ **多格式音频支持**：wav / mp3 / m4a / aac / flac / ogg / wma / amr / opus，自动转换为 16kHz 单声道 16bit PCM
- 🗣️ **讯飞方言识别大模型**：支持普通话及多方言识别，四川话、广东话等轻松搞定
- 🧠 **大模型结构化提取**：基于阿里云百炼 Qwen 模型，自动提取姓名、年龄、症状、简单分析
- 📄 **Word 病历生成**：python-docx 生成格式规范的门诊病历
- 🖱️ **图形界面**：Tkinter + tkinterdnd2，支持拖拽音频、进度展示、历史记录、另存为
- 💾 **中间产物持久化**：转写文本、结构化 JSON 自动保存，方便溯源
- 📊 **处理历史记录**：记录处理时间、音频长度、状态，本地持久化

---

## 技术栈

| 模块 | 技术 |
|------|------|
| 语音识别 | 讯飞开放平台 · 方言识别大模型（WebSocket） |
| 大模型 | 阿里云百炼 · Qwen（OpenAI 兼容接口） |
| 音频处理 | imageio-ffmpeg（内置 ffmpeg，无需系统安装） |
| 文档生成 | python-docx |
| 图形界面 | Tkinter + tkinterdnd2 |
| 配置管理 | python-dotenv |

---

## 项目结构

```
medical-record-agent/
├── main.py                      # 命令行入口
├── gui.py                       # 图形界面入口
├── requirements.txt             # Python 依赖
├── .env                         # 环境变量（凭证等）
├── config/
│   └── settings.py              # 全局配置管理
├── core/
│   ├── pipeline.py              # 主流程编排器
│   └── exceptions.py            # 自定义异常
├── audio/
│   ├── preprocessor.py          # 音频预处理（格式转换+音量标准化）
│   └── splitter.py              # 长音频切割
├── asr/
│   ├── base.py                  # ASR 抽象基类
│   └── xunfei_asr.py            # 讯飞方言识别大模型实现
├── llm/
│   ├── base.py                  # LLM 抽象基类
│   ├── prompt_builder.py        # Prompt 模板构建器
│   └── qwen_client.py           # 阿里云百炼客户端
├── document/
│   ├── validator.py             # 病历数据校验
│   └── word_generator.py        # Word 文档生成
├── utils/
│   └── logger.py                # 日志工具
└── data/
    ├── input/                   # 待处理音频
    └── output/                  # 生成结果（按音频名分子目录）
```

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置凭证

编辑 `.env` 文件，填入讯飞 ASR 和阿里云百炼的凭证：

```env
XUNFEI_APPID=你的APPID
XUNFEI_API_KEY=你的APIKey
XUNFEI_API_SECRET=你的APISecret
LLM_API_KEY=你的百炼APIKey
LLM_BASE_URL=https://你的百炼地址/compatible-mode/v1
LLM_MODEL_NAME=qwen3.7-flash-2026-07-15
```

### 3. 运行

**图形界面（推荐）：**

```bash
python gui.py
```

拖拽音频文件到窗口 → 点击"确认生成病历" → 查看结果 → 打开/另存为 Word。

**命令行：**

```bash
# 单文件
python main.py --audio data/input/录音.m4a

# 批量处理目录
python main.py --audio data/input/ --batch
```

---

## 输出说明

处理完成后，`data/output/{音频名}/` 目录下生成：

| 文件 | 说明 |
|------|------|
| `converted.wav` | 预处理后的标准音频 |
| `transcript.txt` | ASR 转写文本 |
| `structured.json` | LLM 结构化结果 |
| `病历_{姓名}_{时间}.docx` | 最终 Word 病历 |

结构化 JSON 字段：

```json
{
  "patient_name": "患者姓名",
  "patient_age": "患者年龄",
  "symptoms": "症状描述（仅症状，无分析）",
  "simple_analysis": "简单分析（100字以内）"
}
```

---

## 设计亮点

- **ASR 可替换**：通过 `ASRBase` 抽象，后续可无缝切换 Whisper、FunASR 等
- **LLM 可替换**：`QwenClient` 可替换为任意 OpenAI 兼容模型
- **无 ffmpeg 依赖**：`imageio-ffmpeg` 内置二进制，开箱即用
- **同步阻塞 ASR**：用 `threading.Event` 替代全局变量，支持多次调用互不干扰
- **Python 3.14 兼容**：弃用 pydub（依赖已移除的 audioop），改用 ffmpeg 直连

---

## 🤖 关于本项目的开发

本项目由 **TRAE** 智能编程助手全程辅助开发完成。

从架构设计、模块拆分、代码编写到调试排错，TRAE 展现了强大的工程能力：

- ✅ 自动识别 Python 3.14 与 pydub 的兼容问题并给出替代方案
- ✅ 精准定位讯飞 ASR 的 domain 参数错误（`spark_asr_v2` → `slm`）
- ✅ 发现 ffmpeg 音量标准化导致采样率漂移的隐蔽 bug
- ✅ 一次跑通"音频→ASR→LLM→Word"全链路

> 如果你也在写代码，强烈推荐试试 **TRAE**，它真的能让你少掉很多头发。
>
> （TRAE 官方看到的话，广告费结一下呗，我这文案写得不比你们市场部差吧？😏）

---

## License

MIT
