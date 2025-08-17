"""
多模态服务 - 统一的帧提取、嵌入生成和去重服务
"""
import os
import base64
import time
import logging
import tempfile
import shutil
import json
import concurrent.futures
import threading
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path
import cohere
import numpy as np
from ffmpeg_process import VideoProcessor


class MultimodalService:
    """多模态服务 - 统一处理帧提取、嵌入生成和去重"""
    
    # 类常量
    DEFAULT_EMBEDDING_MODEL = "embed-v4.0"
    DEFAULT_BATCH_SIZE = 10
    DEFAULT_API_DELAY = 0.1
    SUPPORTED_IMAGE_FORMATS = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.gif': 'image/gif',
        '.webp': 'image/webp'
    }

    def __init__(self,
                 cohere_api_key: str,
                 ffmpeg_path: str = "ffmpeg",
                 similarity_threshold: float = 0.9,
                 embedding_model: str = DEFAULT_EMBEDDING_MODEL,
                 batch_size: int = DEFAULT_BATCH_SIZE,
                 frame_fps: float = 0.1,
                 max_concurrent_segments: int = 3,
                 logger: Optional[logging.Logger] = None):
        """
        初始化多模态服务
        """
        self.cohere_api_key = cohere_api_key
        self.similarity_threshold = similarity_threshold
        self.embedding_model = embedding_model
        self.batch_size = batch_size
        self.frame_fps = frame_fps
        self.max_concurrent_segments = max_concurrent_segments
        self.cohere_client = cohere.ClientV2(api_key=cohere_api_key)
        self.video_processor = VideoProcessor(ffmpeg_path)
        self.logger = logger or logging.getLogger(__name__)
        self._embedding_lock = threading.Lock()

    def extract_frames(self, video_path: str, start_time: float, end_time: float, 
                      fps: float = 1.0, output_dir: Optional[str] = None) -> List[str]:
        """从视频指定时间范围抽取帧 - 委托给VideoProcessor"""
        return self.video_processor.extract_frames(video_path, start_time, end_time, fps, output_dir)

    def _detect_image_content_type(self, image_path: str) -> str:
        """检测图片的MIME类型"""
        image_path_lower = image_path.lower()
        for ext, content_type in self.SUPPORTED_IMAGE_FORMATS.items():
            if image_path_lower.endswith(ext):
                return content_type
        return "image/jpeg"  # 默认为jpeg

    def _image_to_base64(self, image_path: str) -> str:
        """将图片转换为Cohere需要的base64格式"""
        with open(image_path, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')
            content_type = self._detect_image_content_type(image_path)
            return f"data:{content_type};base64,{image_data}"

    def generate_embeddings(self, image_paths: List[str],
                          batch_size: Optional[int] = None,
                          embedding_lock: Optional[object] = None) -> Tuple[List[np.ndarray], List[str]]:
        """
        批量获取图片embeddings
        """
        if batch_size is None:
            batch_size = self.batch_size

        all_embeddings = []
        successful_paths = []

        for i in range(0, len(image_paths), batch_size):
            batch_paths = image_paths[i:i + batch_size]
            self.logger.info(f"Processing batch {i//batch_size + 1}/{(len(image_paths) + batch_size - 1)//batch_size}")

            # 准备API请求数据
            input_data = []
            batch_valid_paths = []

            for path in batch_paths:
                try:
                    base64_image = self._image_to_base64(path)
                    input_data.append({
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": base64_image}
                            }
                        ]
                    })
                    batch_valid_paths.append(path)
                except Exception as e:
                    self.logger.warning(f"Failed to process image {path}: {e}")
                    continue

            if not input_data:
                continue

            # 调用Cohere API（使用锁保护）
            try:
                if embedding_lock:
                    with embedding_lock:
                        embeddings = self._call_cohere_api(input_data)
                        time.sleep(self.DEFAULT_API_DELAY)
                else:
                    embeddings = self._call_cohere_api(input_data)
                    time.sleep(self.DEFAULT_API_DELAY)

                all_embeddings.extend(embeddings)
                successful_paths.extend(batch_valid_paths)

            except Exception as e:
                self.logger.warning(f"API call failed for batch: {e}")
                continue

        return all_embeddings, successful_paths

    def _call_cohere_api(self, input_data: List[Dict[str, Any]]) -> List[np.ndarray]:
        """调用Cohere API获取embeddings"""
        try:
            response = self.cohere_client.embed(
                model=self.embedding_model,
                input_type="image",
                embedding_types=["float"],
                inputs=input_data
            )

            embeddings = []
            for embedding_data in response.embeddings.float_:
                embedding = np.array(embedding_data)
                embeddings.append(embedding)

            return embeddings

        except Exception as e:
            raise RuntimeError(f"Cohere API error: {e}")

    @staticmethod
    def calculate_cosine_similarity(embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """计算两个向量的余弦相似度"""
        # 归一化向量
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        # 计算余弦相似度
        similarity = np.dot(embedding1, embedding2) / (norm1 * norm2)
        return float(similarity)

    def remove_duplicates(self, image_paths: List[str], 
                         embeddings: List[np.ndarray]) -> List[str]:
        """
        基于embeddings相似度去除重复图片
        """
        if len(image_paths) != len(embeddings):
            raise ValueError("image_paths and embeddings must have the same length")
        
        unique_indices = []
        processed_embeddings = []
        
        for i, current_embedding in enumerate(embeddings):
            is_duplicate = False
            
            # 与已处理的embeddings比较
            for processed_embedding in processed_embeddings:
                similarity = self.calculate_cosine_similarity(current_embedding, processed_embedding)
                if similarity > self.similarity_threshold:
                    is_duplicate = True
                    self.logger.debug(f"Found duplicate: {image_paths[i]} (similarity: {similarity:.3f})")
                    break
            
            if not is_duplicate:
                unique_indices.append(i)
                processed_embeddings.append(current_embedding)
        
        unique_paths = [image_paths[i] for i in unique_indices]
        self.logger.info(f"Removed {len(image_paths) - len(unique_paths)} duplicate images")
        self.logger.info(f"Remaining unique images: {len(unique_paths)}")

        return unique_paths

    def save_unique_frames(self, unique_paths: List[str], output_dir: str,
                          copy_files: bool = True) -> List[str]:
        """
        保存去重后的图片到指定目录
        """
        os.makedirs(output_dir, exist_ok=True)
        saved_paths = []

        for i, src_path in enumerate(unique_paths):
            # 生成新的文件名
            filename = f"unique_frame_{i+1:06d}.jpg"
            dst_path = os.path.join(output_dir, filename)

            try:
                if copy_files:
                    shutil.copy2(src_path, dst_path)
                else:
                    shutil.move(src_path, dst_path)
                saved_paths.append(dst_path)
            except Exception as e:
                self.logger.warning(f"Failed to save {src_path}: {e}")

        self.logger.info(f"Saved {len(saved_paths)} unique frames to {output_dir}")
        return saved_paths

    def process_video_frames(self, video_path: str, start_time: float, end_time: float,
                           output_dir: str, fps: float = 1.0, temp_dir: Optional[str] = None,
                           keep_temp_files: bool = False,
                           embedding_lock: Optional[object] = None) -> Dict[str, Any]:
        """
        视频帧去重处理流程
        """
        self.logger.info(f"Starting video frame deduplication process...")
        self.logger.info(f"Video: {video_path}")
        self.logger.info(f"Time range: {start_time}s - {end_time}s")
        self.logger.info(f"FPS: {fps}")
        self.logger.info(f"Similarity threshold: {self.similarity_threshold}")

        # 创建临时目录
        if temp_dir is None:
            temp_dir = tempfile.mkdtemp(prefix="video_dedup_")
            temp_created = True
        else:
            os.makedirs(temp_dir, exist_ok=True)
            temp_created = False

        try:
            # 1. 抽取帧
            self.logger.info("1. Extracting frames...")
            frame_paths = self.extract_frames(video_path, start_time, end_time, fps, temp_dir)

            # 2. 获取embeddings
            self.logger.info("2. Getting embeddings...")
            embeddings, successful_paths = self.generate_embeddings(frame_paths, embedding_lock=embedding_lock)

            if len(embeddings) != len(frame_paths):
                self.logger.warning(f"Got {len(embeddings)} embeddings for {len(frame_paths)} frames")
                # 使用成功处理的图片路径
                frame_paths = successful_paths

            # 3. 去除重复
            self.logger.info("3. Removing duplicates...")
            unique_paths = self.remove_duplicates(frame_paths, embeddings)

            # 4. 保存结果
            self.logger.info("4. Saving unique frames...")
            saved_paths = self.save_unique_frames(unique_paths, output_dir)

            # 统计信息
            result = {
                "video_path": video_path,
                "time_range": (start_time, end_time),
                "fps": fps,
                "total_frames": len(frame_paths),
                "unique_frames": len(saved_paths),
                "duplicates_removed": len(frame_paths) - len(saved_paths),
                "similarity_threshold": self.similarity_threshold,
                "output_dir": output_dir,
                "saved_paths": saved_paths
            }

            self.logger.info("✅ Process completed successfully!")
            return result

        finally:
            # 清理临时文件
            if temp_created and not keep_temp_files:
                try:
                    shutil.rmtree(temp_dir)
                    self.logger.info(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    self.logger.warning(f"Failed to clean up temp directory: {e}")

    def _parse_time_to_seconds(self, time_str: str) -> float:
        """将时间字符串(HH:MM:SS.mmm)转换为秒数"""
        try:
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

    def extract_segment_frames(self, video_path: str, start_time: str,
                              end_time: str, output_dir: str) -> List[str]:
        """提取指定时间段的视频帧并去重"""
        start_seconds = self._parse_time_to_seconds(start_time)
        end_seconds = self._parse_time_to_seconds(end_time)

        segment_dir = os.path.join(output_dir, f"segment_{start_time.replace(':', '-')}_to_{end_time.replace(':', '-')}")
        os.makedirs(segment_dir, exist_ok=True)

        try:
            result = self.process_video_frames(
                video_path=video_path,
                start_time=start_seconds,
                end_time=end_seconds,
                output_dir=segment_dir,
                fps=self.frame_fps,
                keep_temp_files=False,
                embedding_lock=self._embedding_lock
            )
            return result.get("saved_paths", [])
        except Exception as e:
            self.logger.error(f"时间段 {start_time}-{end_time} 帧处理失败: {e}")
            return []

    def _process_single_segment(self, segment_data: tuple) -> dict:
        """处理单个时间段的帧提取"""
        i, segment, video_path, frames_dir, output_dir = segment_data
        start_time = segment.get("start_time", "")
        end_time = segment.get("end_time", "")
        summary = segment.get("summary", "")

        try:
            frame_paths = self.extract_segment_frames(video_path, start_time, end_time, frames_dir)
            relative_frame_paths = [os.path.relpath(path, output_dir) for path in frame_paths]
        except Exception as e:
            self.logger.error(f"时间段 {start_time}-{end_time} 帧提取失败: {e}")
            relative_frame_paths = []

        return {
            "segment_id": i + 1,
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": self._parse_time_to_seconds(end_time) - self._parse_time_to_seconds(start_time),
            "summary": summary,
            "key_frames": relative_frame_paths,
            "frame_count": len(relative_frame_paths)
        }

    def generate_multimodal_notes(self, video_path: str, summary_json_path: str, output_dir: str) -> str:
        """生成图文混排笔记（支持时间段级别并发处理）"""
        # 读取摘要数据
        with open(summary_json_path, 'r', encoding='utf-8') as f:
            summary_data = json.load(f)

        summaries = summary_data.get("summaries", [])
        if not summaries:
            raise ValueError("摘要数据为空")

        os.makedirs(output_dir, exist_ok=True)
        frames_dir = os.path.join(output_dir, "frames")
        os.makedirs(frames_dir, exist_ok=True)

        segment_tasks = [(i, segment, video_path, frames_dir, output_dir)
                        for i, segment in enumerate(summaries)]

        multimodal_notes = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrent_segments) as executor:
            future_to_index = {executor.submit(self._process_single_segment, task_data): task_data[0]
                              for task_data in segment_tasks}

            results = {}
            for future in concurrent.futures.as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except Exception as e:
                    self.logger.error(f"时间段 {index+1} 处理失败: {e}")
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

            for i in range(len(summaries)):
                if i in results:
                    multimodal_notes.append(results[i])

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

        output_file = os.path.join(output_dir, "multimodal_notes.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(final_notes, f, ensure_ascii=False, indent=4)

        return output_file

    def export_to_markdown(self, notes_json_path: str, output_path: str = None,
                          image_base_path: str = None) -> str:
        """将图文笔记导出为 Markdown 格式"""
        with open(notes_json_path, 'r', encoding='utf-8') as f:
            notes_data = json.load(f)

        if output_path is None:
            output_path = f"{Path(notes_json_path).stem}.md"
        if image_base_path is None:
            image_base_path = str(Path(notes_json_path).parent)

        markdown_content = self._generate_markdown_content(notes_data, output_path, image_base_path)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)

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

                    # 直接拼接正确的路径
                    if image_base_path:
                        image_path = f"/{image_base_path}/multimodal_notes/{frame_path}"
                    else:
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


def create_multimodal_service(cohere_api_key: str, **kwargs) -> MultimodalService:
    """便捷函数：创建多模态服务"""
    return MultimodalService(cohere_api_key, **kwargs)
