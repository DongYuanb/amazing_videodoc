#!/usr/bin/env python3
"""
图文混排笔记生成器 - 将视频转换为结构化的图文笔记
支持多种导出格式：JSON、Markdown、HTML
"""
import os
import logging
import json
from pathlib import Path
import concurrent.futures
import threading
from typing import List, Dict, Any, Optional
from datetime import datetime
from video_frame_deduplicator import VideoFrameDeduplicator
from dotenv import load_dotenv
load_dotenv()

cohere_api_key = os.getenv("COHERE_API_KEY")

class MultimodalNoteGenerator:
    """图文混排笔记生成器"""
    
    def __init__(self,
                 cohere_api_key: str,
                 ffmpeg_path: str = "ffmpeg",
                 frame_fps: float = 0.5,  # 每2秒抽一帧
                 similarity_threshold: float = 0.9,
                 max_concurrent_segments: int = 3,
                 logger: Optional[logging.Logger] = None):
        """
        初始化图文笔记生成器

        Args:
            cohere_api_key: Cohere API密钥（用于图片去重）
            ffmpeg_path: ffmpeg路径
            frame_fps: 抽帧频率（每秒帧数）
            similarity_threshold: 图片相似度阈值
            max_concurrent_segments: 最大并发处理的时间段数量
            logger: 日志记录器
        """
        if not cohere_api_key:
            raise ValueError("COHERE_API_KEY 不能为空")

        self.logger = logger or logging.getLogger(__name__)

        self.logger.info("🔧 初始化图文笔记生成器...")
        self.logger.info(f"   - Cohere API Key: {'已设置' if cohere_api_key else '未设置'}")
        self.logger.info(f"   - FFmpeg路径: {ffmpeg_path}")
        self.logger.info(f"   - 抽帧频率: {frame_fps} fps")

        try:
            self.frame_deduplicator = VideoFrameDeduplicator(
                cohere_api_key=cohere_api_key,
                ffmpeg_path=ffmpeg_path,
                similarity_threshold=similarity_threshold,
                logger=self.logger
            )
            self.frame_fps = frame_fps
            self.max_concurrent_segments = max_concurrent_segments
            # 用于保护embedding API调用的锁（确保embedding阶段串行）
            self._embedding_lock = threading.Lock()
            self.logger.info("✅ 图文笔记生成器初始化成功")
        except Exception as e:
            self.logger.error(f"❌ VideoFrameDeduplicator 初始化失败: {e}")
            raise
    
    def _parse_time_to_seconds(self, time_str: str) -> float:
        """
        将时间字符串转换为秒数
        
        Args:
            time_str: 时间字符串，格式如 "00:14:31.180"
            
        Returns:
            秒数（浮点数）
        """
        try:
            # 解析 HH:MM:SS.mmm 格式
            time_parts = time_str.split(':')
            hours = int(time_parts[0])
            minutes = int(time_parts[1])
            seconds_parts = time_parts[2].split('.')
            seconds = int(seconds_parts[0])
            milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
            
            total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
            return total_seconds
        except (ValueError, IndexError) as e:
            raise ValueError(f"无法解析时间格式: {time_str}, 错误: {e}")
    
    def extract_segment_frames(self,
                              video_path: str,
                              start_time: str,
                              end_time: str,
                              output_dir: str) -> List[str]:
        """
        提取指定时间段的视频帧并去重

        Args:
            video_path: 视频文件路径
            start_time: 开始时间字符串
            end_time: 结束时间字符串
            output_dir: 输出目录

        Returns:
            去重后的帧图片路径列表
        """
        # 转换时间格式
        start_seconds = self._parse_time_to_seconds(start_time)
        end_seconds = self._parse_time_to_seconds(end_time)

        # 创建该时间段的输出目录
        segment_dir = os.path.join(output_dir, f"segment_{start_time.replace(':', '-')}_to_{end_time.replace(':', '-')}")
        os.makedirs(segment_dir, exist_ok=True)

        # 使用完整的处理流程（抽帧 + 去重）
        try:
            # 不在这里加锁，让抽帧等步骤可以并发
            result = self.frame_deduplicator.process_video_frames(
                video_path=video_path,
                start_time=start_seconds,
                end_time=end_seconds,
                output_dir=segment_dir,
                fps=self.frame_fps,
                keep_temp_files=False,
                embedding_lock=self._embedding_lock  # 传递锁给去重器
            )

            # 获取实际的文件路径列表
            saved_paths = result.get("saved_paths", [])
            total_frames = result.get("total_frames", 0)
            unique_count = result.get("unique_frames", 0)

            self.logger.info(f"✅ 时间段 {start_time}-{end_time}: {total_frames} 帧 → {unique_count} 帧（去重后）")
            return saved_paths

        except Exception as e:
            self.logger.error(f"❌ 时间段 {start_time}-{end_time} 帧处理失败: {e}")
            return []

    def _process_single_segment(self, segment_data: tuple) -> dict:
        """
        处理单个时间段的帧提取（用于并发调用）

        Args:
            segment_data: (segment_index, segment_dict, video_path, frames_dir, output_dir)

        Returns:
            处理结果字典
        """
        i, segment, video_path, frames_dir, output_dir = segment_data

        start_time = segment.get("start_time", "")
        end_time = segment.get("end_time", "")
        summary = segment.get("summary", "")

        self.logger.info(f"📝 处理时间段 {i+1}: {start_time} - {end_time}")

        # 提取该时间段的关键帧
        try:
            frame_paths = self.extract_segment_frames(
                video_path=video_path,
                start_time=start_time,
                end_time=end_time,
                output_dir=frames_dir
            )

            # 转换为相对路径（便于后续处理）
            relative_frame_paths = [
                os.path.relpath(path, output_dir) for path in frame_paths
            ]

        except Exception as e:
            self.logger.error(f"❌ 时间段 {start_time}-{end_time} 帧提取失败: {e}")
            relative_frame_paths = []

        # 构建该时间段的笔记数据
        note_segment = {
            "segment_id": i + 1,
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": self._parse_time_to_seconds(end_time) - self._parse_time_to_seconds(start_time),
            "summary": summary,
            "key_frames": relative_frame_paths,
            "frame_count": len(relative_frame_paths)
        }

        return note_segment
    
    def generate_multimodal_notes(self,
                                 video_path: str,
                                 summary_json_path: str,
                                 output_dir: str) -> str:
        """
        生成图文混排笔记（支持时间段级别并发处理）

        Args:
            video_path: 视频文件路径
            summary_json_path: 摘要JSON文件路径
            output_dir: 输出目录

        Returns:
            生成的图文笔记JSON文件路径
        """
        # 读取摘要数据
        with open(summary_json_path, 'r', encoding='utf-8') as f:
            summary_data = json.load(f)

        summaries = summary_data.get("summaries", [])
        if not summaries:
            raise ValueError("摘要数据为空")

        self.logger.info(f"🎬 开始生成图文笔记，共 {len(summaries)} 个时间段")
        self.logger.info(f"🔄 并发处理，最大并发数: {self.max_concurrent_segments}")

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        frames_dir = os.path.join(output_dir, "frames")
        os.makedirs(frames_dir, exist_ok=True)

        # 准备并发处理的数据
        segment_tasks = [
            (i, segment, video_path, frames_dir, output_dir)
            for i, segment in enumerate(summaries)
        ]

        # 使用线程池并发处理时间段
        multimodal_notes = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrent_segments) as executor:
            # 提交所有任务
            future_to_index = {
                executor.submit(self._process_single_segment, task_data): task_data[0]
                for task_data in segment_tasks
            }

            # 收集结果（按原始顺序）
            results = {}
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    result = future.result()
                    results[index] = result
                    self.logger.info(f"✅ 时间段 {index+1} 处理完成")
                except Exception as e:
                    self.logger.error(f"❌ 时间段 {index+1} 处理失败: {e}")
                    # 创建一个空的结果
                    segment = summaries[index]
                    results[index] = {
                        "segment_id": index + 1,
                        "start_time": segment.get("start_time", ""),
                        "end_time": segment.get("end_time", ""),
                        "duration_seconds": 0,
                        "summary": segment.get("summary", ""),
                        "key_frames": [],
                        "frame_count": 0
                    }

            # 按顺序排列结果
            for i in range(len(summaries)):
                if i in results:
                    multimodal_notes.append(results[i])

        # 生成最终的图文笔记数据
        final_notes = {
            "video_info": {
                "source_video": os.path.basename(video_path),
                "total_segments": len(multimodal_notes),
                "generated_at": datetime.now().isoformat(),
                "processing_mode": f"concurrent (max_workers={self.max_concurrent_segments})"
            },
            "segments": multimodal_notes,
            "statistics": {
                "total_frames": sum(note["frame_count"] for note in multimodal_notes),
                "segments_with_frames": len([note for note in multimodal_notes if note["frame_count"] > 0])
            }
        }

        # 保存图文笔记
        output_file = os.path.join(output_dir, "multimodal_notes.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_notes, f, ensure_ascii=False, indent=4)

        self.logger.info("🎉 图文笔记生成完成!")
        self.logger.info(f"📄 笔记文件: {output_file}")
        self.logger.info("📊 统计信息:")
        self.logger.info(f"   - 总时间段: {final_notes['statistics']['segments_with_frames']}/{len(multimodal_notes)}")
        self.logger.info(f"   - 总关键帧: {final_notes['statistics']['total_frames']}")
        self.logger.info(f"   - 处理模式: 并发处理 (最大{self.max_concurrent_segments}个线程)")

        return output_file

    def export_to_markdown(self, notes_json_path: str, output_path: str = None,
                          image_base_path: str = None) -> str:
        """
        将图文笔记导出为 Markdown 格式

        Args:
            notes_json_path: 图文笔记 JSON 文件路径
            output_path: 输出 Markdown 文件路径
            image_base_path: 图片基础路径（用于计算相对路径）

        Returns:
            生成的 Markdown 文件路径
        """
        # 读取笔记数据
        with open(notes_json_path, 'r', encoding='utf-8') as f:
            notes_data = json.load(f)

        if output_path is None:
            output_path = f"{Path(notes_json_path).stem}.md"

        # 如果没有指定图片基础路径，使用笔记文件的目录
        if image_base_path is None:
            image_base_path = str(Path(notes_json_path).parent)

        # 生成 Markdown 内容
        markdown_content = self._generate_markdown_content(notes_data, output_path, image_base_path)

        # 保存文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

        self.logger.info(f"📝 Markdown 笔记已导出: {output_path}")
        return output_path


    def _generate_markdown_content(self, notes_data: Dict[str, Any],
                                  output_path: str = None,
                                  image_base_path: str = None) -> str:
        """生成 Markdown 内容"""
        video_info = notes_data.get("video_info", {})
        segments = notes_data.get("segments", [])
        statistics = notes_data.get("statistics", {})

        # 构建 Markdown
        lines = []

        # 标题和基本信息
        lines.append(f"# 📹 视频笔记：{video_info.get('source_video', '未知视频')}")
        lines.append("")
        lines.append("## 📊 基本信息")
        lines.append("")
        lines.append(f"- **视频文件**: {video_info.get('source_video', '未知')}")
        lines.append(f"- **生成时间**: {video_info.get('generated_at', '未知')}")
        lines.append(f"- **总时间段**: {video_info.get('total_segments', 0)}")
        lines.append(f"- **总关键帧**: {statistics.get('total_frames', 0)}")
        lines.append(f"- **有效时间段**: {statistics.get('segments_with_frames', 0)}")
        lines.append("")

        # 目录
        lines.append("## 📑 目录")
        lines.append("")
        for i, segment in enumerate(segments, 1):
            start_time = segment.get("start_time", "")
            end_time = segment.get("end_time", "")
            lines.append(f"{i}. [{start_time} - {end_time}](#时间段-{i})")
        lines.append("")

        # 详细内容
        lines.append("## 📝 详细内容")
        lines.append("")

        for i, segment in enumerate(segments, 1):
            start_time = segment.get("start_time", "")
            end_time = segment.get("end_time", "")
            duration = segment.get("duration_seconds", 0)
            summary = segment.get("summary", "")
            key_frames = segment.get("key_frames", [])

            # 时间段标题
            lines.append(f"### 时间段 {i}")
            lines.append("")
            lines.append(f"**⏰ 时间**: {start_time} - {end_time} ({duration:.1f}秒)")
            lines.append("")

            # 摘要内容
            lines.append("**📋 摘要**:")
            lines.append("")
            lines.append(summary)
            lines.append("")

            # 关键帧
            if key_frames:
                lines.append(f"**🖼️ 关键帧** ({len(key_frames)}张):")
                lines.append("")
                for frame_path in key_frames:
                    frame_name = Path(frame_path).name

                    # 直接拼接正确的路径：/storage/tasks/{task_id}/multimodal_notes/frames/segment_xxx/unique_frame_xxx.jpg
                    if image_base_path:
                        # image_base_path 是 task_dir，即 /storage/tasks/{task_id}
                        image_path = f"/{image_base_path}/multimodal_notes/{frame_path}"
                    else:
                        # 备用方案
                        image_path = f"multimodal_notes/{frame_path}"

                    lines.append(f"![{frame_name}]({image_path})")
                lines.append("")
            else:
                lines.append("*该时间段无关键帧*")
                lines.append("")

            lines.append("---")
            lines.append("")

        # 页脚
        lines.append("## 🔧 生成信息")
        lines.append("")
        lines.append("本笔记由视频处理 API 自动生成")
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if output_path:
            lines.append(f"输出文件: {output_path}")

        return "\n".join(lines)



# 便捷函数
def generate_video_notes(video_path: str,
                        summary_json_path: str,
                        output_dir: str,
                        cohere_api_key: str,
                        frame_fps: float = 0.5,
                        max_concurrent_segments: int = 3,
                        logger: Optional[logging.Logger] = None) -> str:
    """
    便捷函数：生成视频的图文混排笔记（支持并发处理）

    Args:
        video_path: 视频文件路径
        summary_json_path: 摘要JSON文件路径
        output_dir: 输出目录
        cohere_api_key: COHERE_API_KEY密钥
        frame_fps: 抽帧频率
        max_concurrent_segments: 最大并发处理的时间段数量
        logger: 日志记录器

    Returns:
        生成的图文笔记JSON文件路径
    """
    generator = MultimodalNoteGenerator(
        cohere_api_key=cohere_api_key,
        frame_fps=frame_fps,
        max_concurrent_segments=max_concurrent_segments,
        logger=logger
    )
    
    return generator.generate_multimodal_notes(
        video_path=video_path,
        summary_json_path=summary_json_path,
        output_dir=output_dir
    )


