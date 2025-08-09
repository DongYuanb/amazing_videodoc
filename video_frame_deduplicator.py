import os
import subprocess
import tempfile
import base64
import time
import logging
from typing import List, Optional, Dict, Any, Tuple
import cohere
import numpy as np
import shutil


class VideoFrameDeduplicator:
    """视频帧去重处理器：抽取视频帧，使用Cohere API获取embeddings，去除相似帧"""

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
                 api_timeout: int = 30,
                 embedding_model: str = DEFAULT_EMBEDDING_MODEL,
                 batch_size: int = DEFAULT_BATCH_SIZE,
                 logger: Optional[logging.Logger] = None):
        """
        初始化去重处理器

        Args:
            cohere_api_key: Cohere API密钥
            ffmpeg_path: ffmpeg可执行文件路径
            similarity_threshold: 相似度阈值，超过此值认为是重复图片
            api_timeout: API请求超时时间（秒）
            embedding_model: 使用的embedding模型名称
            batch_size: 批处理大小
            logger: 日志记录器
        """
        self.cohere_api_key = cohere_api_key
        self.ffmpeg_path = ffmpeg_path
        self.similarity_threshold = similarity_threshold
        self.api_timeout = api_timeout
        self.embedding_model = embedding_model
        self.batch_size = batch_size
        self.cohere_client = cohere.ClientV2(api_key=cohere_api_key)
        self.logger = logger or logging.getLogger(__name__)

    def extract_frames(self, 
                      video_path: str, 
                      start_time: float, 
                      end_time: float, 
                      fps: float = 1.0,
                      output_dir: Optional[str] = None) -> List[str]:
        """
        从视频指定时间范围抽取帧
        
        Args:
            video_path: 视频文件路径
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
            fps: 抽帧频率（每秒帧数）
            output_dir: 输出目录，如果为None则使用临时目录
            
        Returns:
            抽取的帧图片路径列表
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        if start_time >= end_time:
            raise ValueError("start_time must be less than end_time")
        
        # 创建输出目录
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="video_frames_")
        else:
            os.makedirs(output_dir, exist_ok=True)
        
        # 构建ffmpeg命令
        duration = end_time - start_time
        output_pattern = os.path.join(output_dir, "frame_%06d.jpg")
        
        cmd = [
            self.ffmpeg_path,
            "-i", video_path,
            "-ss", str(start_time),
            "-t", str(duration),
            "-vf", f"fps={fps}",
            "-y",  # 覆盖输出文件
            output_pattern
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True, text=True)
            self.logger.info(f"Frame extraction completed. Output: {output_dir}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg failed: {e.stderr}")
        
        # 获取生成的图片文件列表
        frame_files = []
        for file in sorted(os.listdir(output_dir)):
            if file.startswith("frame_") and file.endswith(".jpg"):
                frame_files.append(os.path.join(output_dir, file))
        
        if not frame_files:
            raise RuntimeError("No frames were extracted")
        
        self.logger.info(f"Extracted {len(frame_files)} frames")
        return frame_files
    
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
    
    def get_batch_embeddings(self,
                               image_paths: List[str],
                               batch_size: Optional[int] = None,
                               embedding_lock: Optional[object] = None) -> Tuple[List[np.ndarray], List[str]]:
        """
        批量获取图片embeddings

        Args:
            image_paths: 图片路径列表
            batch_size: 批处理大小，如果为None则使用默认值
            embedding_lock: 用于保护API调用的锁

        Returns:
            (embeddings向量列表, 成功处理的图片路径列表)
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
    
    def remove_duplicates(self, 
                         image_paths: List[str], 
                         embeddings: List[np.ndarray]) -> List[str]:
        """
        基于embeddings相似度去除重复图片
        
        Args:
            image_paths: 图片路径列表
            embeddings: 对应的embeddings列表
            
        Returns:
            去重后的图片路径列表
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

    def save_unique_frames(self,
                          unique_paths: List[str],
                          output_dir: str,
                          copy_files: bool = True) -> List[str]:
        """
        保存去重后的图片到指定目录

        Args:
            unique_paths: 去重后的图片路径列表
            output_dir: 输出目录
            copy_files: 是否复制文件，False则移动文件

        Returns:
            保存后的图片路径列表
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

    def process_video_frames(self,
                           video_path: str,
                           start_time: float,
                           end_time: float,
                           output_dir: str,
                           fps: float = 1.0,
                           temp_dir: Optional[str] = None,
                           keep_temp_files: bool = False,
                           embedding_lock: Optional[object] = None) -> Dict[str, Any]:
        """
        完整的视频帧去重处理流程

        Args:
            video_path: 视频文件路径
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
            output_dir: 最终输出目录
            fps: 抽帧频率
            temp_dir: 临时目录，如果为None则自动创建
            keep_temp_files: 是否保留临时文件
            embedding_lock: 用于保护embedding API调用的锁（并发控制）

        Returns:
            处理结果字典，包含统计信息和文件路径
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
            embeddings, successful_paths = self.get_batch_embeddings(frame_paths, embedding_lock=embedding_lock)

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


def create_deduplicator(cohere_api_key: str, **kwargs) -> VideoFrameDeduplicator:
    """便捷函数：创建视频帧去重处理器"""
    return VideoFrameDeduplicator(cohere_api_key, **kwargs)

