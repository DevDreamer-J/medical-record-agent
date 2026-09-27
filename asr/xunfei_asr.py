"""
讯飞 WebSocket ASR 实现（方言识别大模型）
参考官方 demo spark_slm_iat.py
domain=slm, accent=mulacc
"""
import base64
import hashlib
import hmac
import json
import ssl
import threading
import time
from datetime import datetime
from time import mktime
from urllib.parse import urlencode
from wsgiref.handlers import format_date_time

import websocket

from asr.base import ASRBase
from core.exceptions import ASRRecognitionError
from utils.logger import get_logger

logger = get_logger(__name__)

STATUS_FIRST_FRAME = 0
STATUS_CONTINUE_FRAME = 1
STATUS_LAST_FRAME = 2


class XunfeiASR(ASRBase):
    """讯飞方言识别大模型 ASR 实现"""

    def __init__(self, appid: str, api_key: str, api_secret: str,
                 ws_url: str = "wss://iat.cn-huabei-1.xf-yun.com/v1",
                 hotwords: list = None):
        self.appid = appid
        self.api_key = api_key
        self.api_secret = api_secret
        self.ws_url = ws_url
        self.hotwords = hotwords or []

        # 运行时状态
        self._result = ""
        self._done_event = None
        self._error = None

    def recognize(self, audio_path: str) -> str:
        """识别单个音频文件，返回完整文本"""
        self._result = ""
        self._error = None
        self._done_event = threading.Event()

        ws_url = self._build_ws_url()
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        ws.on_open = lambda w: self._on_open(w, audio_path)

        logger.info(f"开始识别: {audio_path}")
        ws.run_forever(
            sslopt={"cert_reqs": ssl.CERT_NONE},
            ping_interval=10,
            ping_timeout=5,
        )

        # 等待结果完成（最多 120 秒）
        if not self._done_event.wait(timeout=120):
            raise ASRRecognitionError("ASR 识别超时")

        if self._error:
            raise ASRRecognitionError(f"ASR 识别失败: {self._error}")

        logger.info(f"识别完成，文本长度: {len(self._result)}")
        return self._result

    def _build_ws_url(self) -> str:
        """构建讯飞 WebSocket 鉴权 URL"""
        host = "iat.cn-huabei-1.xf-yun.com"
        path = "/v1"
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
        signature_sha = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        signature_sha = base64.b64encode(signature_sha).decode("utf-8")

        authorization_origin = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature_sha}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")

        v = {
            "authorization": authorization,
            "date": date,
            "host": host,
        }
        return self.ws_url + "?" + urlencode(v)

    def _iat_params(self) -> dict:
        """构建 iat 请求参数（方言识别大模型 slm）"""
        params = {
            "domain": "slm",
            "language": "zh_cn",
            "accent": "mulacc",
            "result": {
                "encoding": "utf8",
                "compress": "raw",
                "format": "json",
            },
        }
        return params

    def _send_audio(self, ws, audio_path: str):
        """分帧发送音频数据（参考官方 demo）"""
        frame_size = 1280  # 16kHz 16bit 单声道 40ms = 1280 字节
        interval = 0.04
        status = STATUS_FIRST_FRAME
        iat_params = self._iat_params()

        try:
            with open(audio_path, "rb") as fp:
                # 跳过 WAV 文件头（44字节），只发送 PCM 数据
                wav_marker = fp.read(4)
                if wav_marker == b"RIFF":
                    fp.seek(44, 0)
                else:
                    fp.seek(0, 0)

                while True:
                    buf = fp.read(frame_size)
                    audio_b64 = base64.b64encode(buf).decode("utf-8")

                    # 文件结束
                    if not buf:
                        status = STATUS_LAST_FRAME

                    if status == STATUS_FIRST_FRAME:
                        d = {
                            "header": {
                                "status": STATUS_FIRST_FRAME,
                                "app_id": self.appid,
                            },
                            "parameter": {"iat": iat_params},
                            "payload": {
                                "audio": {
                                    "audio": audio_b64,
                                    "sample_rate": 16000,
                                    "encoding": "raw",
                                }
                            },
                        }
                        ws.send(json.dumps(d))
                        status = STATUS_CONTINUE_FRAME

                    elif status == STATUS_CONTINUE_FRAME:
                        d = {
                            "header": {
                                "status": STATUS_CONTINUE_FRAME,
                                "app_id": self.appid,
                            },
                            "payload": {
                                "audio": {
                                    "audio": audio_b64,
                                    "sample_rate": 16000,
                                    "encoding": "raw",
                                }
                            },
                        }
                        ws.send(json.dumps(d))

                    elif status == STATUS_LAST_FRAME:
                        d = {
                            "header": {
                                "status": STATUS_LAST_FRAME,
                                "app_id": self.appid,
                            },
                            "payload": {
                                "audio": {
                                    "audio": audio_b64,
                                    "sample_rate": 16000,
                                    "encoding": "raw",
                                }
                            },
                        }
                        ws.send(json.dumps(d))
                        break

                    time.sleep(interval)
        except FileNotFoundError:
            self._error = f"音频文件不存在: {audio_path}"
            self._done_event.set()
        except Exception as e:
            self._error = f"发送音频异常: {e}"
            self._done_event.set()

    def _on_open(self, ws, audio_path: str):
        """连接建立后，启动发送线程"""
        threading.Thread(target=self._send_audio, args=(ws, audio_path), daemon=True).start()

    def _on_message(self, ws, message: str):
        """WebSocket 消息回调，收集识别结果"""
        try:
            msg = json.loads(message)
            header = msg.get("header", {})
            code = header.get("code", -1)
            status = header.get("status", -1)

            if code != 0:
                self._error = f"ASR 错误 code={code}, sid={header.get('sid', '')}"
                self._done_event.set()
                ws.close()
                return

            payload = msg.get("payload")
            if payload:
                result = payload.get("result", {})
                text_b64 = result.get("text")
                if text_b64:
                    text_json = json.loads(base64.b64decode(text_b64).decode("utf-8"))
                    ws_list = text_json.get("ws", [])
                    for item in ws_list:
                        for cw in item.get("cw", []):
                            self._result += cw.get("w", "")

            if status == STATUS_LAST_FRAME:
                self._done_event.set()
                ws.close()
        except Exception as e:
            self._error = f"消息处理异常: {e}"
            self._done_event.set()

    def _on_error(self, ws, error):
        self._error = f"WebSocket 错误: {error}"
        self._done_event.set()

    def _on_close(self, ws, close_status_code, close_msg):
        if not self._done_event.is_set():
            self._done_event.set()
