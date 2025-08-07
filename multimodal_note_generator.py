#!/usr/bin/env python3
"""
图文混排笔记生成器 - 将视频转换为结构化的图文笔记
支持多种导出格式：JSON、Markdown、HTML
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from video_frame_deduplicator import VideoFrameDeduplicator
from dotenv import load_dotenv
load_dotenv()

jina_api_key = os.getenv("JINA_API_KEY")

class MultimodalNoteGenerator:
    """图文混排笔记生成器"""
    
    def __init__(self,
                 jina_api_key: str,
                 ffmpeg_path: str = "ffmpeg",
                 frame_fps: float = 0.5,  # 每2秒抽一帧
                 similarity_threshold: float = 0.9):
        """
        初始化图文笔记生成器

        Args:
            jina_api_key: Jina API密钥（用于图片去重）
            ffmpeg_path: ffmpeg路径
            frame_fps: 抽帧频率（每秒帧数）
            similarity_threshold: 图片相似度阈值
        """
        if not jina_api_key:
            raise ValueError("jina_api_key 不能为空")

        print(f"🔧 初始化图文笔记生成器...")
        print(f"   - Jina API Key: {'已设置' if jina_api_key else '未设置'}")
        print(f"   - FFmpeg路径: {ffmpeg_path}")
        print(f"   - 抽帧频率: {frame_fps} fps")

        try:
            self.frame_deduplicator = VideoFrameDeduplicator(
                jina_api_key=jina_api_key,
                ffmpeg_path=ffmpeg_path,
                similarity_threshold=similarity_threshold
            )
            self.frame_fps = frame_fps
            print("✅ 图文笔记生成器初始化成功")
        except Exception as e:
            print(f"❌ VideoFrameDeduplicator 初始化失败: {e}")
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
            result = self.frame_deduplicator.process_video_frames(
                video_path=video_path,
                start_time=start_seconds,
                end_time=end_seconds,
                output_dir=segment_dir,
                fps=self.frame_fps,
                keep_temp_files=False
            )

            # 获取实际的文件路径列表
            saved_paths = result.get("saved_paths", [])
            total_frames = result.get("total_frames", 0)
            unique_count = result.get("unique_frames", 0)

            print(f"✅ 时间段 {start_time}-{end_time}: {total_frames} 帧 → {unique_count} 帧（去重后）")
            return saved_paths

        except Exception as e:
            print(f"❌ 时间段 {start_time}-{end_time} 帧处理失败: {e}")
            return []
    
    def generate_multimodal_notes(self,
                                 video_path: str,
                                 summary_json_path: str,
                                 output_dir: str) -> str:
        """
        生成图文混排笔记
        
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
        
        print(f"🎬 开始生成图文笔记，共 {len(summaries)} 个时间段")
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        frames_dir = os.path.join(output_dir, "frames")
        os.makedirs(frames_dir, exist_ok=True)
        
        multimodal_notes = []
        
        for i, segment in enumerate(summaries):
            start_time = segment.get("start_time", "")
            end_time = segment.get("end_time", "")
            summary = segment.get("summary", "")
            
            print(f"\n📝 处理时间段 {i+1}/{len(summaries)}: {start_time} - {end_time}")
            
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
                print(f"❌ 时间段 {start_time}-{end_time} 帧提取失败: {e}")
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
            
            multimodal_notes.append(note_segment)
        
        # 生成最终的图文笔记数据
        final_notes = {
            "video_info": {
                "source_video": os.path.basename(video_path),
                "total_segments": len(multimodal_notes),
                "generated_at": datetime.now().isoformat()
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
        
        print(f"\n🎉 图文笔记生成完成!")
        print(f"📄 笔记文件: {output_file}")
        print(f"📊 统计信息:")
        print(f"   - 总时间段: {final_notes['statistics']['segments_with_frames']}/{len(multimodal_notes)}")
        print(f"   - 总关键帧: {final_notes['statistics']['total_frames']}")
        
        return output_file


# 便捷函数
def generate_video_notes(video_path: str,
                        summary_json_path: str,
                        output_dir: str,
                        jina_api_key: str,
                        frame_fps: float = 0.5) -> str:
    """
    便捷函数：生成视频的图文混排笔记
    
    Args:
        video_path: 视频文件路径
        summary_json_path: 摘要JSON文件路径
        output_dir: 输出目录
        jina_api_key: Jina API密钥
        frame_fps: 抽帧频率
        
    Returns:
        生成的图文笔记JSON文件路径
    """
    generator = MultimodalNoteGenerator(
        jina_api_key=jina_api_key,
        frame_fps=frame_fps
    )
    
    return generator.generate_multimodal_notes(
        video_path=video_path,
        summary_json_path=summary_json_path,
        output_dir=output_dir
    )


if __name__ == "__main__":
    # 测试用例
    import sys
    
    if len(sys.argv) < 4:
        print("用法: python multimodal_note_generator.py <视频文件> <摘要JSON> <输出目录> [Jina API Key]")
        sys.exit(1)
    
    video_file = sys.argv[1]
    summary_file = sys.argv[2]
    output_directory = sys.argv[3]
    api_key = sys.argv[4] if len(sys.argv) > 4 else os.getenv("JINA_API_KEY")
    
    if not api_key:
        print("❌ 请提供 Jina API Key")
        sys.exit(1)
    
    try:
        result = generate_video_notes(
            video_path=video_file,
            summary_json_path=summary_file,
            output_dir=output_directory,
            jina_api_key=api_key
        )
        print(f"✅ 成功生成图文笔记: {result}")
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        sys.exit(1)
