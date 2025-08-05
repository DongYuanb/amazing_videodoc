import os
import subprocess
import tempfile
import base64
import json
import time
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import requests
import numpy as np
from PIL import Image
import shutil


class VideoFrameDeduplicator:
    """视频帧去重处理器：抽取视频帧，使用Jina API获取embeddings，去除相似帧"""
    
    def __init__(self, 
                 jina_api_key: str,
                 ffmpeg_path: str = "ffmpeg",
                 similarity_threshold: float = 0.9,
                 api_timeout: int = 30):
        """
        初始化去重处理器
        
        Args:
            jina_api_key: Jina API密钥
            ffmpeg_path: ffmpeg可执行文件路径
            similarity_threshold: 相似度阈值，超过此值认为是重复图片
            api_timeout: API请求超时时间（秒）
        """
        self.jina_api_key = jina_api_key
        self.ffmpeg_path = ffmpeg_path
        self.similarity_threshold = similarity_threshold
        self.api_timeout = api_timeout
        self.jina_api_url = "https://api.jina.ai/v1/embeddings"
        
        self._check_ffmpeg()
    
    def _check_ffmpeg(self):
        """检查ffmpeg可用性"""
        try:
            subprocess.run([self.ffmpeg_path, "-version"], 
                         capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(f"ffmpeg not found at {self.ffmpeg_path}")
    
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
            result = subprocess.run(cmd, capture_output=True, check=True, text=True)
            print(f"Frame extraction completed. Output: {output_dir}")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg failed: {e.stderr}")
        
        # 获取生成的图片文件列表
        frame_files = []
        for file in sorted(os.listdir(output_dir)):
            if file.startswith("frame_") and file.endswith(".jpg"):
                frame_files.append(os.path.join(output_dir, file))
        
        if not frame_files:
            raise RuntimeError("No frames were extracted")
        
        print(f"Extracted {len(frame_files)} frames")
        return frame_files
    
    def _image_to_base64(self, image_path: str) -> str:
        """将图片转换为base64编码"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def get_batch_embeddings(self, image_paths: List[str], batch_size: int = 10) -> List[np.ndarray]:
        """
        批量获取图片embeddings
        
        Args:
            image_paths: 图片路径列表
            batch_size: 批处理大小
            
        Returns:
            embeddings向量列表
        """
        all_embeddings = []
        
        for i in range(0, len(image_paths), batch_size):
            batch_paths = image_paths[i:i + batch_size]
            print(f"Processing batch {i//batch_size + 1}/{(len(image_paths) + batch_size - 1)//batch_size}")
            
            # 准备API请求数据
            input_data = []
            for path in batch_paths:
                try:
                    base64_image = self._image_to_base64(path)
                    input_data.append({"image": base64_image})
                except Exception as e:
                    print(f"Warning: Failed to process image {path}: {e}")
                    continue
            
            if not input_data:
                continue
            
            # 调用Jina API
            try:
                embeddings = self._call_jina_api(input_data)
                all_embeddings.extend(embeddings)
                
                # 添加延迟避免API限制
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Warning: API call failed for batch: {e}")
                continue
        
        return all_embeddings
    
    def _call_jina_api(self, input_data: List[Dict[str, Any]]) -> List[np.ndarray]:
        """调用Jina API获取embeddings"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.jina_api_key}"
        }
        
        payload = {
            "model": "jina-clip-v2",
            "input": input_data
        }
        
        response = requests.post(
            self.jina_api_url,
            headers=headers,
            json=payload,
            timeout=self.api_timeout
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"Jina API error: {response.status_code} - {response.text}")
        
        result = response.json()
        embeddings = []
        
        for item in result.get("data", []):
            embedding = np.array(item["embedding"])
            embeddings.append(embedding)
        
        return embeddings
    
    def calculate_cosine_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
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
                    print(f"Found duplicate: {image_paths[i]} (similarity: {similarity:.3f})")
                    break
            
            if not is_duplicate:
                unique_indices.append(i)
                processed_embeddings.append(current_embedding)
        
        unique_paths = [image_paths[i] for i in unique_indices]
        print(f"Removed {len(image_paths) - len(unique_paths)} duplicate images")
        print(f"Remaining unique images: {len(unique_paths)}")
        
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
                print(f"Warning: Failed to save {src_path}: {e}")

        print(f"Saved {len(saved_paths)} unique frames to {output_dir}")
        return saved_paths

    def process_video_frames(self,
                           video_path: str,
                           start_time: float,
                           end_time: float,
                           output_dir: str,
                           fps: float = 1.0,
                           temp_dir: Optional[str] = None,
                           keep_temp_files: bool = False) -> Dict[str, Any]:
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

        Returns:
            处理结果字典，包含统计信息和文件路径
        """
        print(f"Starting video frame deduplication process...")
        print(f"Video: {video_path}")
        print(f"Time range: {start_time}s - {end_time}s")
        print(f"FPS: {fps}")
        print(f"Similarity threshold: {self.similarity_threshold}")

        # 创建临时目录
        if temp_dir is None:
            temp_dir = tempfile.mkdtemp(prefix="video_dedup_")
            temp_created = True
        else:
            os.makedirs(temp_dir, exist_ok=True)
            temp_created = False

        try:
            # 1. 抽取帧
            print("\n1. Extracting frames...")
            frame_paths = self.extract_frames(video_path, start_time, end_time, fps, temp_dir)

            # 2. 获取embeddings
            print("\n2. Getting embeddings...")
            embeddings = self.get_batch_embeddings(frame_paths)

            if len(embeddings) != len(frame_paths):
                print(f"Warning: Got {len(embeddings)} embeddings for {len(frame_paths)} frames")
                # 只处理成功获取embedding的图片
                min_len = min(len(embeddings), len(frame_paths))
                frame_paths = frame_paths[:min_len]
                embeddings = embeddings[:min_len]

            # 3. 去除重复
            print("\n3. Removing duplicates...")
            unique_paths = self.remove_duplicates(frame_paths, embeddings)

            # 4. 保存结果
            print("\n4. Saving unique frames...")
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

            print(f"\n✅ Process completed successfully!")
            print(f"Total frames extracted: {result['total_frames']}")
            print(f"Unique frames saved: {result['unique_frames']}")
            print(f"Duplicates removed: {result['duplicates_removed']}")
            print(f"Output directory: {output_dir}")

            return result

        finally:
            # 清理临时文件
            if temp_created and not keep_temp_files:
                try:
                    shutil.rmtree(temp_dir)
                    print(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e:
                    print(f"Warning: Failed to clean up temp directory: {e}")


def create_deduplicator(jina_api_key: str, **kwargs) -> VideoFrameDeduplicator:
    """便捷函数：创建视频帧去重处理器"""
    return VideoFrameDeduplicator(jina_api_key, **kwargs)


# 使用示例
if __name__ == "__main__":
    # 示例用法
    api_key = "jina_1eab753c55994fe0973e7996d65e9432j_ghOOZ4ayKDNh0J4WgKZGC1Ihqt"

    # 创建处理器
    deduplicator = VideoFrameDeduplicator(
        jina_api_key=api_key,
        similarity_threshold=0.95,  # 提高相似度阈值，只去除非常相似的帧
    )

    # 处理视频
    result = deduplicator.process_video_frames(
        video_path="/Users/musk/Documents/code/amazing_videodoc/upload/demo_video.mp4",
        start_time=10.0,  # 从10秒开始
        end_time=60.0,    # 到60秒结束
        output_dir="output/unique_frames",
        fps=1,          # 每1秒抽取1帧，减少抽帧频率
    )

    print("VideoFrameDeduplicator ready")
