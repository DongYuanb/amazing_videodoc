#!/usr/bin/env python3
"""
图文混排笔记生成器 - 门面类，委托给MultimodalService处理
"""
import logging
from typing import Optional
from services.multimodal_service import MultimodalService


class MultimodalNoteGenerator:
    """图文混排笔记生成器 - 门面类，保持向后兼容"""

    def __init__(self,
                 cohere_api_key: str,
                 ffmpeg_path: str = "ffmpeg",
                 frame_fps: float = 0.2,
                 similarity_threshold: float = 0.9,
                 max_concurrent_segments: int = 3,
                 logger: Optional[logging.Logger] = None):
        """
        初始化图文笔记生成器
        """
        if not cohere_api_key:
            raise ValueError("COHERE_API_KEY 不能为空")

        self.logger = logger or logging.getLogger(__name__)

        try:
            self.multimodal_service = MultimodalService(
                cohere_api_key=cohere_api_key,
                ffmpeg_path=ffmpeg_path,
                similarity_threshold=similarity_threshold,
                frame_fps=frame_fps,
                max_concurrent_segments=max_concurrent_segments,
                enable_text_alignment=True,  # 启用图文对齐
                max_aligned_frames=3,        # 每段最多3帧
                logger=self.logger
            )
        except Exception as e:
            self.logger.error(f"MultimodalService 初始化失败: {e}")
            raise

    def generate_multimodal_notes(self, video_path: str, summary_json_path: str, output_dir: str) -> str:
        """生成图文混排笔记 - 委托给MultimodalService"""
        return self.multimodal_service.generate_multimodal_notes(video_path, summary_json_path, output_dir)

    def export_to_markdown(self, notes_json_path: str, output_path: str = None,
                          image_base_path: str = None) -> str:
        """导出Markdown格式 - 委托给MultimodalService"""
        return self.multimodal_service.export_to_markdown(notes_json_path, output_path, image_base_path)



