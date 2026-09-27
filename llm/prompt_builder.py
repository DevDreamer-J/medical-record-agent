"""
病历结构化 Prompt 构建器
提取字段：姓名、年龄、症状（纯症状，无分析）、简单分析（100字内）
"""


class PromptBuilder:
    """病历结构化 Prompt 构建器"""

    DEFAULT_TEMPLATE = """你是一名专业的医疗文书助手。请根据以下医患对话的语音转写文本，提取关键信息生成结构化病历。

要求：
1. 严格按照以下 JSON 格式输出，不要输出任何多余内容
2. 医学术语要规范化（如"肚子疼"→"腹痛"）
3. 如果某项信息对话中未提及，填 null
4. "symptoms" 字段只填写患者自述的症状，不要包含任何分析或判断
5. "simple_analysis" 字段为医生的简单分析，控制在 100 字以内

输出格式：
{{
  "patient_name": "患者姓名",
  "patient_age": "患者年龄（如：35岁）",
  "symptoms": "症状描述（仅症状，无分析）",
  "simple_analysis": "简单分析（100字以内）"
}}

对话文本：
{transcript}"""

    def build(self, transcript: str, template: str = None) -> str:
        """构建完整的 Prompt"""
        tpl = template or self.DEFAULT_TEMPLATE
        return tpl.format(transcript=transcript)
