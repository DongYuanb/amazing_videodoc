"""视频处理工作流服务"""
import os
import logging
from typing import Dict

from services.text_merge import TextMerger
from services.summary_generator import Summarizer
from .asr_tencent.asr_service import ASRService
from services.ffmpeg_process import extract_audio_for_asr
from services.multimodal_note_generator import MultimodalNoteGenerator
from utils.step_decorators import run_step
from settings import get_settings

class VideoProcessingWorkflow:
    """视频处理工作流程"""

    def __init__(self, enable_multimodal: bool = True, task_logger: logging.Logger = None, task_manager=None, task_id: str | None = None):
        self.enable_multimodal = enable_multimodal
        self.logger = task_logger or logging.getLogger(__name__)
        self.task_manager = task_manager
        self.task_id = task_id
        self._init_services()

    def _init_services(self):
        """初始化所有服务"""
        settings = get_settings()
        model_id = settings.MODEL_ID

        # 核心服务
        self.text_merger = TextMerger(model_id)
        self.summary_generator = Summarizer(model_id)
        self.asr_service = self._create_asr_service()

        # 可选服务
        self.multimodal_generator = self._create_multimodal_generator() if self.enable_multimodal else None
        if self.multimodal_generator and self.task_id:
            # 将task_id传递，隔离缓存
            try:self.multimodal_generator.__init__(task_id=self.task_id,logger=self.logger)
            except Exception as e:self.logger.warning(f"无法为多模态服务设置task_id: {e}")

    def _create_asr_service(self):
        """创建ASR服务"""
        try:
            s = get_settings()
            return ASRService(s.TENCENT_APPID, s.TENCENT_SECRET_ID, s.TENCENT_SECRET_KEY)
        except ValueError as e:
            raise RuntimeError(f"ASR服务初始化失败: {e}")

    def _create_multimodal_generator(self):
        """创建图文笔记生成器（从集中配置读取，无需传参）"""
        try:
            return MultimodalNoteGenerator(logger=self.logger,task_id=self.task_id)
        except Exception as e:
            self.logger.warning(f"跳过图文笔记生成: {e}");return None

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
            run_step("extract_audio", extract_audio_for_asr, video_path, audio_path, task_manager=self.task_manager, task_id=self.task_id, logger=self.logger)

            # 2. ASR转录
            run_step("asr", self._asr_with_progress, audio_path, asr_json, task_manager=self.task_manager, task_id=self.task_id, logger=self.logger)

            # 3. 文本合并
            success = run_step("merge_text", self.text_merger.process_file, asr_json, merged_json, task_manager=self.task_manager, task_id=self.task_id, logger=self.logger)
            if not success:
                raise RuntimeError("文本合并失败")

            # 4. 生成摘要
            success = run_step("summary", self.summary_generator.process_file, merged_json, summary_json, task_manager=self.task_manager, task_id=self.task_id, logger=self.logger)
            if not success:
                raise RuntimeError("摘要生成失败")

            # 5. 生成图文笔记（可选）
            if self.enable_multimodal and self.multimodal_generator:
                notes_dir = os.path.join(output_dir, "multimodal_notes")
                multimodal_notes = run_step("multimodal", self._multimodal_with_progress,
                    video_path, summary_json, notes_dir,
                    task_manager=self.task_manager, task_id=self.task_id, logger=self.logger
                )
            else:
                multimodal_notes = None

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
            if self.task_manager and self.task_id:
                self.task_manager.update_status(self.task_id, "failed", str(e))
            raise

    def _asr_with_progress(self,audio,asr_out):
        import wave,threading,time;from settings import get_settings
        s=get_settings();tm=self.task_manager;tid=self.task_id;step="asr"
        try:
            with wave.open(audio,"rb") as w:dur=w.getnframes()/w.getframerate()
        except:dur=60
        est=max(s.ASR_PROGRESS_MIN_SECS,dur/s.ASR_PROGRESS_SPEED_X);t0=time.time();done=False
        def tick():
            while not done:
                f=min(0.99,(time.time()-t0)/est);tm.update_progress(tid,step,f);time.sleep(1)
        th=threading.Thread(target=tick,daemon=True);th.start()
        try:return self.asr_service.transcribe_audio(audio,asr_out)
        finally:done=True;th.join(timeout=0.1)

    def _multimodal_with_progress(self,video_path,summary_json,notes_dir):
        progress=lambda f:self.task_manager.update_progress(self.task_id,"multimodal",f)
        return self.multimodal_generator.generate_multimodal_notes(video_path,summary_json,notes_dir,progress_cb=progress)
