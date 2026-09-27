"""自定义异常类"""


class MedicalRecordAgentError(Exception):
    """Agent 基础异常类"""
    pass


class AudioProcessError(MedicalRecordAgentError):
    """音频处理异常"""
    pass


class ASRRecognitionError(MedicalRecordAgentError):
    """语音识别异常"""
    pass


class LLMInferenceError(MedicalRecordAgentError):
    """大模型推理异常"""
    pass


class DocumentGenerateError(MedicalRecordAgentError):
    """文档生成异常"""
    pass
