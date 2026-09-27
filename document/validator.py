"""
病历数据校验器
在生成 Word 前检查关键字段是否缺失，给出警告
"""
from utils.logger import get_logger

logger = get_logger(__name__)


class RecordValidator:
    """病历数据校验器"""

    REQUIRED_FIELDS = ["patient_name", "patient_age", "symptoms"]

    def validate(self, record: dict) -> list:
        """校验病历数据完整性，返回警告信息列表"""
        warnings = []
        warnings.extend(self._check_missing_fields(record))
        return warnings

    def _check_missing_fields(self, record: dict) -> list:
        """检查必填字段是否缺失"""
        warnings = []
        for field in self.REQUIRED_FIELDS:
            value = record.get(field)
            if not value or str(value).strip() == "" or value == "null":
                warnings.append(f"必填字段缺失或为空: {field}")
        return warnings
