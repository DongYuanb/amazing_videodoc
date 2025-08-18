# -*- coding: utf-8 -*-
"""
ASR 服务模块 - 封装腾讯云语音识别功能
"""
import json
import os
import asyncio
from typing import Optional, Dict, Any, List
from pathlib import Path

from . import credential
from . import flash_recognizer


class ASRService:
    """腾讯云 ASR 服务封装类"""
    
    def __init__(self, 
                 appid: str,
                 secret_id: str, 
                 secret_key: str,
                 engine_type: str = "16k_zh"):
        """
        初始化 ASR 服务
        """
        if not appid:
            raise ValueError("APPID 不能为空")
        if not secret_id:
            raise ValueError("SECRET_ID 不能为空")
        if not secret_key:
            raise ValueError("SECRET_KEY 不能为空")
            
        self.appid = appid
        self.secret_id = secret_id
        self.secret_key = secret_key
        self.engine_type = engine_type
        
        # 初始化认证和识别器
        self.credential_var = credential.Credential(secret_id, secret_key)
        self.recognizer = flash_recognizer.FlashRecognizer(appid, self.credential_var)
    
    def _create_request(self) -> flash_recognizer.FlashRecognitionRequest:
        """创建识别请求对象"""
        req = flash_recognizer.FlashRecognitionRequest(self.engine_type)
        req.set_filter_modal(0)
        req.set_filter_punc(0)
        req.set_filter_dirty(0)
        req.set_voice_format("wav")
        req.set_word_info(2)
        req.set_convert_num_mode(1)
        return req
    
    def transcribe_audio(self, 
                        audio_path: str, 
                        output_path: Optional[str] = None) -> str:
        """
        转录音频文件
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        if output_path is None:
            output_path = f"{Path(audio_path).stem}_asr.json"
        
        # 创建识别请求
        req = self._create_request()
        
        try:
            # 读取音频数据
            with open(audio_path, 'rb') as f:
                data = f.read()
            
            # 执行识别
            result_data = self.recognizer.recognize(req, data)
            resp = json.loads(result_data)
            
            # 检查响应状态
            request_id = resp.get("request_id", "")
            code = resp.get("code", -1)
            
            if code != 0:
                message = resp.get("message", "未知错误")
                raise RuntimeError(f"ASR识别失败 - request_id: {request_id}, code: {code}, message: {message}")
            
            # 提取句子信息
            sentences = self._extract_sentences(resp)
            
            # 保存结果
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(sentences, f, ensure_ascii=False, indent=4)
            
            print(f"ASR转录完成: {output_path}")
            return output_path

        except json.JSONDecodeError as e:
            raise RuntimeError(f"ASR响应解析失败: {e}")
        except IOError as e:
            raise RuntimeError(f"文件操作失败: {e}")
        except Exception as e:
            raise RuntimeError(f"ASR转录失败: {e}")

    async def transcribe_audio_async(self,
                                   audio_path: str,
                                   output_path: Optional[str] = None) -> str:
        """
        异步转录音频文件
        """
        try:
            # 在线程池中执行同步方法
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.transcribe_audio,
                audio_path,
                output_path
            )
            return result
        except Exception:
            raise



    def get_detailed_status(self) -> Dict[str, Any]:
        """获取详细的服务状态信息"""
        return {
            "service": "ASR",
            "provider": "Tencent Cloud",
            "config": self.get_recognition_info(),
            "engine_type": self.engine_type,
            "status": "ready"
        }

    def _extract_sentences(self, resp: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从响应中提取句子信息
        """
        sentences = []
        
        flash_result = resp.get("flash_result", [])
        for channel_result in flash_result:
            sentence_list = channel_result.get("sentence_list", [])
            for sentence in sentence_list:
                sentences.append({
                    "text": sentence.get("text", ""),
                    "start_time": sentence.get("start_time", 0),
                    "end_time": sentence.get("end_time", 0)
                })
        
        return sentences
    
    def get_recognition_info(self) -> Dict[str, str]:
        """获取识别器配置信息"""
        return {
            "appid": self.appid,
            "engine_type": self.engine_type,
            "secret_id": self.secret_id[:8] + "***"  # 只显示前8位，保护隐私
        }


# 为了向后兼容，提供一个简单的工厂函数
def create_asr_service(appid: str = None, 
                      secret_id: str = None, 
                      secret_key: str = None,
                      engine_type: str = "16k_zh") -> ASRService:
    """
    创建 ASR 服务实例的工厂函数
    """
    if not appid:
        appid = os.getenv("TENCENT_APPID")
    if not secret_id:
        secret_id = os.getenv("TENCENT_SECRET_ID")
    if not secret_key:
        secret_key = os.getenv("TENCENT_SECRET_KEY")
    
    return ASRService(appid, secret_id, secret_key, engine_type)
