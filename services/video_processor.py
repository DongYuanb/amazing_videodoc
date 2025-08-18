"""视频处理工作流服务"""
import os
import logging
from typing import Dict

from services.text_merge import TextMerger
from services.summary_generator import Summarizer
from .asr_tencent.asr_service import ASRService
from ffmpeg_process import extract_audio_for_asr
from multimodal_note_generator import MultimodalNoteGenerator


class VideoProcessingWorkflow:
    """视频处理工作流程"""

    def __init__(self, enable_multimodal: bool = True, task_logger: logging.Logger = None):
        self.enable_multimodal = enable_multimodal
        self.logger = task_logger or logging.getLogger(__name__)
        self._init_services()

    def _init_services(self):
        """初始化所有服务"""
        model_id = os.getenv("MODEL_ID")

        # 核心服务
        self.text_merger = TextMerger(model_id)
        self.summary_generator = Summarizer(model_id)
        self.asr_service = self._create_asr_service()

        # 可选服务
        self.multimodal_generator = self._create_multimodal_generator() if self.enable_multimodal else None

    def _create_asr_service(self):
        """创建ASR服务"""
        try:
            return ASRService(
                os.getenv("TENCENT_APPID"),
                os.getenv("TENCENT_SECRET_ID"),
                os.getenv("TENCENT_SECRET_KEY")
            )
        except ValueError as e:
            raise RuntimeError(f"ASR服务初始化失败: {e}")

    def _create_multimodal_generator(self):
        """创建图文笔记生成器"""
        cohere_api_key = os.getenv("COHERE_API_KEY")
        if not cohere_api_key:
            self.logger.warning("未提供 Cohere API Key，跳过图文笔记生成")
            return None

        try:
            return MultimodalNoteGenerator(
                cohere_api_key=cohere_api_key,
                ffmpeg_path=os.getenv("FFMPEG_PATH", "ffmpeg")
            )
        except Exception as e:
            self.logger.error(f"图文笔记生成器初始化失败: {e}")
            return None

    def process_video(self, video_path: str, output_dir: str, keep_temp: bool = False) -> Dict[str, str]:
        """处理视频的完整流程"""
        os.makedirs(output_dir, exist_ok=True)

        self.logger.info(f"开始处理视频: {video_path}")
        self.logger.info(f"输出目录: {output_dir}")

        # 定义文件路径
        audio_path = os.path.join(output_dir, "audio.wav")
        asr_json = os.path.join(output_dir, "asr_result.json")
        merged_json = os.path.join(output_dir, "merged_text.json")
        summary_json = os.path.join(output_dir, "summary.json")
        multimodal_notes = None

        try:
            # 1. 提取音频
            self.logger.info("1️⃣ 提取音频...")
            extract_audio_for_asr(video_path, audio_path)

            # 2. ASR转录
            self.logger.info("2️⃣ ASR转录...")
            self.asr_service.transcribe_audio(audio_path, asr_json)

            # 3. 文本合并
            self.logger.info("3️⃣ 文本合并...")
            success = self.text_merger.process_file(asr_json, merged_json)
            if not success:
                raise RuntimeError("文本合并失败")

            # 4. 生成摘要
            self.logger.info("4️⃣ 生成摘要...")
            success = self.summary_generator.process_file(merged_json, summary_json)
            if not success:
                raise RuntimeError("摘要生成失败")

            # 5. 生成图文笔记（可选）
            if self.enable_multimodal and self.multimodal_generator:
                self.logger.info("5️⃣ 生成图文笔记...")
                notes_dir = os.path.join(output_dir, "multimodal_notes")
                multimodal_notes = self.multimodal_generator.generate_multimodal_notes(
                    video_path=video_path,
                    summary_json_path=summary_json,
                    output_dir=notes_dir
                )

            # 清理临时文件
            if not keep_temp:
                try:
                    os.unlink(audio_path)
                    self.logger.info("清理临时音频文件")
                except:
                    pass

            self.logger.info("✅ 处理完成！")
            return {
                "video_path": video_path,
                "output_dir": output_dir,
                "asr_result": asr_json,
                "merged_text": merged_json,
                "summary": summary_json,
                "multimodal_notes": multimodal_notes
            }

        except Exception as e:
            self.logger.error(f"❌ 处理失败: {e}")
            raise
