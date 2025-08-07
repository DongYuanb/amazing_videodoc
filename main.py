#!/usr/bin/env python3
"""
视频处理工作流程编排器 - FastAPI 服务
"""
import os
import json
import uuid
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from asr_tencent.text_merge import TextMerger
from asr_tencent.summary_generator import Summarizer
from asr_tencent.asr_service import ASRService
from ffmpeg_process import extract_audio_for_asr
from multimodal_note_generator import MultimodalNoteGenerator

load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('video_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# API 数据模型
class TaskStatus(BaseModel):
    task_id: str
    status: str  # pending, processing, completed, failed
    current_step: Optional[str] = None
    progress: float = 0.0
    created_at: str
    updated_at: str
    error_message: Optional[str] = None

class ProcessRequest(BaseModel):
    start_from: str = "audio_extract"
    enable_multimodal: bool = True
    keep_temp: bool = False

# 简单的任务管理器
class TaskManager:
    """基于文件系统的简单任务管理"""

    def __init__(self, storage_dir: str = "storage"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.tasks_dir = self.storage_dir / "tasks"
        self.tasks_dir.mkdir(exist_ok=True)

    def create_task(self, original_filename: str) -> str:
        """创建新任务"""
        task_id = str(uuid.uuid4())
        task_dir = self.tasks_dir / task_id
        task_dir.mkdir(exist_ok=True)

        # 创建任务元数据
        metadata = {
            "task_id": task_id,
            "original_filename": original_filename,
            "status": "pending",
            "current_step": None,
            "progress": 0.0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "error_message": None
        }

        self.save_metadata(task_id, metadata)
        return task_id

    def get_task_dir(self, task_id: str) -> Path:
        """获取任务目录"""
        return self.tasks_dir / task_id

    def save_metadata(self, task_id: str, metadata: dict):
        """保存任务元数据"""
        task_dir = self.get_task_dir(task_id)
        with open(task_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def load_metadata(self, task_id: str) -> dict:
        """加载任务元数据"""
        task_dir = self.get_task_dir(task_id)
        metadata_file = task_dir / "metadata.json"
        if not metadata_file.exists():
            raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")

        with open(metadata_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def update_status(self, task_id: str, status: str, current_step: str = None,
                     progress: float = None, error_message: str = None):
        """更新任务状态"""
        metadata = self.load_metadata(task_id)
        metadata["status"] = status
        metadata["updated_at"] = datetime.now().isoformat()

        if current_step is not None:
            metadata["current_step"] = current_step
        if progress is not None:
            metadata["progress"] = progress
        if error_message is not None:
            metadata["error_message"] = error_message

        self.save_metadata(task_id, metadata)

class VideoProcessingWorkflow:
    """视频处理工作流程编排器：专注于流程编排，功能模块解耦"""

    def __init__(self,
                 model_id:str="openrouter/horizon-beta",
                 ffmpeg_path:str="ffmpeg",
                 asr_appid:str=None,
                 asr_secret_id:str=None,
                 asr_secret_key:str=None,
                 jina_api_key:str=None,
                 enable_multimodal:bool=True):
        self.model_id=model_id
        self.enable_multimodal = enable_multimodal

        # 初始化各个功能模块
        self.ffmpeg_path = ffmpeg_path
        self.text_merger = TextMerger(model_id)
        self.summary_generator = Summarizer(model_id)
        self.asr_service = self._init_asr_service(asr_appid, asr_secret_id, asr_secret_key)

        # 初始化图文笔记生成器（如果启用）
        if self.enable_multimodal:
            self.multimodal_generator = self._init_multimodal_generator(jina_api_key, ffmpeg_path)

    def _init_asr_service(self, appid, secret_id, secret_key):
        """初始化 ASR 服务"""
        # 如果没有提供参数，尝试从环境变量或默认值获取
        if not appid:
            appid = os.getenv("TENCENT_APPID")
        if not secret_id:
            secret_id = os.getenv("TENCENT_SECRET_ID")
        if not secret_key:
            secret_key = os.getenv("TENCENT_SECRET_KEY")

        try:
            return ASRService(appid, secret_id, secret_key)
        except ValueError as e:
            raise RuntimeError(f"ASR服务初始化失败: {e}")

    def _init_multimodal_generator(self, jina_api_key, ffmpeg_path):
        """初始化图文笔记生成器"""
        if not jina_api_key:
            jina_api_key = os.getenv("JINA_API_KEY")

        logger.info(f"🔧 检查 Jina API Key: {'已设置' if jina_api_key else '未设置'}")

        if not jina_api_key:
            logger.warning("⚠️  未提供 Jina API Key，将跳过图文笔记生成")
            return None

        try:
            logger.info("🔧 正在初始化图文笔记生成器...")
            generator = MultimodalNoteGenerator(
                jina_api_key=jina_api_key,
                ffmpeg_path=ffmpeg_path
            )
            logger.info("✅ 图文笔记生成器初始化成功")
            return generator
        except Exception as e:
            logger.error(f"⚠️  图文笔记生成器初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def extract_audio(self,video_path:str,output_audio:Optional[str]=None)->str:
        """从视频中提取音频（委托给ffmpeg_process模块）"""
        return extract_audio_for_asr(video_path, output_audio, self.ffmpeg_path)
    
    def run_asr(self,audio_path:str,output_json:Optional[str]=None,
               progress_callback=None)->str:
        """运行ASR转录（使用ASR服务模块）"""
        if output_json is None:
            output_json=f"{Path(audio_path).stem}_asr.json"

        try:
            if progress_callback:
                return self.asr_service.transcribe_audio_with_progress(
                    audio_path, output_json, progress_callback
                )
            else:
                return self.asr_service.transcribe_audio(audio_path, output_json)
        except Exception as e:
            raise RuntimeError(f"ASR转录失败: {e}")
    
    def merge_texts(self,asr_json:str,output_merged:Optional[str]=None,
                   progress_callback=None)->str:
        """合并ASR文本"""
        if output_merged is None:
            output_merged=f"{Path(asr_json).stem}_merged.json"

        try:
            if progress_callback:
                success = self.text_merger.process_file_with_progress(
                    asr_json, output_merged, progress_callback
                )
            else:
                success = self.text_merger.process_file(asr_json, output_merged)

            if success:
                logger.info(f"文本合并完成: {output_merged}")
                return output_merged
            else:
                raise RuntimeError("文本合并失败")
        except Exception as e:
            raise RuntimeError(f"文本合并失败: {e}")
    
    def generate_summary(self,merged_json:str,output_summary:Optional[str]=None,
                        progress_callback=None)->str:
        """生成摘要"""
        if output_summary is None:
            output_summary=f"{Path(merged_json).stem}_summary.json"

        try:
            if progress_callback:
                success = self.summary_generator.process_file_with_progress(
                    merged_json, output_summary, progress_callback
                )
            else:
                success = self.summary_generator.process_file(merged_json, output_summary)

            if success:
                logger.info(f"摘要生成完成: {output_summary}")
                return output_summary
            else:
                raise RuntimeError("摘要生成失败")
        except Exception as e:
            raise RuntimeError(f"摘要生成失败: {e}")

    def generate_multimodal_notes(self, video_path:str, summary_json:str, output_dir:str)->Optional[str]:
        """生成图文混排笔记"""
        if not self.enable_multimodal or not self.multimodal_generator:
            logger.warning("⚠️  图文笔记生成功能未启用或初始化失败")
            return None

        try:
            notes_dir = os.path.join(output_dir, "multimodal_notes")
            notes_file = self.multimodal_generator.generate_multimodal_notes(
                video_path=video_path,
                summary_json_path=summary_json,
                output_dir=notes_dir
            )
            logger.info(f"图文笔记生成完成: {notes_file}")
            return notes_file
        except Exception as e:
            logger.error(f"⚠️  图文笔记生成失败: {e}")
            return None

    def process_from_existing(self,
                             video_path: str,
                             existing_output_dir: str,
                             start_from: str = "multimodal") -> Dict[str, str]:
        """
        从已有的输出目录继续处理

        Args:
            video_path: 原视频文件路径
            existing_output_dir: 已有的输出目录
            start_from: 从哪个步骤开始

        Returns:
            处理结果字典
        """
        if not os.path.exists(existing_output_dir):
            raise FileNotFoundError(f"输出目录不存在: {existing_output_dir}")

        # 检测已有文件
        existing_files = {}
        potential_files = {
            "audio": "audio.wav",
            "asr": "asr_result.json",
            "merged": "merged_text.json",
            "summary": "summary.json"
        }

        for key, filename in potential_files.items():
            file_path = os.path.join(existing_output_dir, filename)
            if os.path.exists(file_path):
                existing_files[key] = file_path
                logger.info(f"✅ 发现已有文件: {key} -> {file_path}")

        if not existing_files:
            raise ValueError(f"在目录 {existing_output_dir} 中未找到任何可用的中间文件")

        return self.process_video(
            video_path=video_path,
            output_dir=existing_output_dir,
            start_from=start_from,
            existing_files=existing_files
        )


    def process_video(self,
                     video_path:str,
                     output_dir:Optional[str]=None,
                     keep_temp:bool=False,
                     start_from:str="audio_extract",
                     existing_files:Optional[Dict[str,str]]=None,
                     progress_callback=None)->Dict[str,str]:
        """
        灵活的视频处理流程，支持从任意步骤开始

        Args:
            video_path: 视频文件路径
            output_dir: 输出目录
            keep_temp: 是否保留临时文件
            start_from: 从哪个步骤开始 ("audio_extract", "asr", "text_merge", "summary", "multimodal")
            existing_files: 已存在的文件路径字典，用于跳过前面的步骤
        """
        if output_dir is None:
            output_dir=f"output_{Path(video_path).stem}"

        os.makedirs(output_dir,exist_ok=True)

        logger.info(f"🎬 开始处理视频: {video_path}")
        logger.info(f"📁 输出目录: {output_dir}")
        logger.info(f"🚀 从步骤开始: {start_from}")

        # 初始化文件路径（确保不为None）
        audio_path = existing_files.get("audio") if existing_files else os.path.join(output_dir,"audio.wav")
        asr_json = existing_files.get("asr") if existing_files else os.path.join(output_dir,"asr_result.json")
        merged_json = existing_files.get("merged") if existing_files else os.path.join(output_dir,"merged_text.json")
        summary_json = existing_files.get("summary") if existing_files else os.path.join(output_dir,"summary.json")

        # 如果从existing_files获取的路径为None，使用默认路径
        if audio_path is None:
            audio_path = os.path.join(output_dir,"audio.wav")
        if asr_json is None:
            asr_json = os.path.join(output_dir,"asr_result.json")
        if merged_json is None:
            merged_json = os.path.join(output_dir,"merged_text.json")
        if summary_json is None:
            summary_json = os.path.join(output_dir,"summary.json")

        multimodal_notes = None

        try:
            # 1. 提取音频
            if start_from == "audio_extract":
                logger.info("1️⃣ 提取音频...")
                audio_path=self.extract_audio(video_path,audio_path)
            elif audio_path and os.path.exists(audio_path):
                logger.info(f"✅ 跳过音频提取，使用现有文件: {audio_path}")

            # 2. ASR转录
            if start_from in ["audio_extract", "asr"]:
                logger.info("2️⃣ ASR转录...")
                asr_json=self.run_asr(audio_path,asr_json,progress_callback)
            elif asr_json and os.path.exists(asr_json):
                logger.info(f"✅ 跳过ASR转录，使用现有文件: {asr_json}")

            # 3. 文本合并
            if start_from in ["audio_extract", "asr", "text_merge"]:
                logger.info("3️⃣ 文本合并...")
                merged_json=self.merge_texts(asr_json,merged_json,progress_callback)
            elif merged_json and os.path.exists(merged_json):
                logger.info(f"✅ 跳过文本合并，使用现有文件: {merged_json}")

            # 4. 生成摘要
            if start_from in ["audio_extract", "asr", "text_merge", "summary"]:
                logger.info("4️⃣ 生成摘要...")
                summary_json=self.generate_summary(merged_json,summary_json,progress_callback)
            elif summary_json and os.path.exists(summary_json):
                logger.info(f"✅ 跳过摘要生成，使用现有文件: {summary_json}")
            else:
                # 如果是从multimodal开始，但没有summary文件，报错
                if start_from == "multimodal":
                    raise FileNotFoundError(f"图文笔记生成需要摘要文件，但文件不存在: {summary_json}")

            # 5. 生成图文混排笔记
            if self.enable_multimodal and start_from in ["audio_extract", "asr", "text_merge", "summary", "multimodal"]:
                logger.info("5️⃣ 生成图文混排笔记...")
                multimodal_notes = self.generate_multimodal_notes(video_path, summary_json, output_dir)

            # 清理临时文件
            if not keep_temp:
                try:
                    os.unlink(audio_path)
                    logger.info("🧹 清理临时音频文件")
                except:pass

            result={
                "video_path":video_path,
                "output_dir":output_dir,
                "asr_result":asr_json,
                "merged_text":merged_json,
                "summary":summary_json,
                "multimodal_notes":multimodal_notes
            }
            
            logger.info("✅ 处理完成！")
            logger.info(f"📄 ASR结果: {asr_json}")
            logger.info(f"📝 合并文本: {merged_json}")
            logger.info(f"📋 摘要: {summary_json}")
            if multimodal_notes:
                logger.info(f"🎨 图文笔记: {multimodal_notes}")

            return result

        except Exception as e:
            logger.error(f"❌ 处理失败: {e}")
            raise

# ==================== FastAPI 应用 ====================
# 创建 FastAPI 应用
app = FastAPI(
    title="视频处理 API",
    description="视频转录、摘要和图文笔记生成服务",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {"message": "视频处理 API 服务", "docs": "/docs"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    """上传视频文件"""
    if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
        raise HTTPException(status_code=400, detail="不支持的视频格式")

    # 创建任务
    task_id = task_manager.create_task(file.filename)
    task_dir = task_manager.get_task_dir(task_id)

    # 保存上传的文件
    video_path = task_dir / "original_video.mp4"
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "task_id": task_id,
        "filename": file.filename,
        "message": "文件上传成功"
    }

@app.post("/api/process/{task_id}")
async def start_processing(task_id: str, request: ProcessRequest, background_tasks: BackgroundTasks):
    """开始处理视频"""
    try:
        metadata = task_manager.load_metadata(task_id)
    except:
        raise HTTPException(status_code=404, detail="任务不存在")

    if metadata["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"任务状态错误: {metadata['status']}")

    # 启动后台处理
    background_tasks.add_task(
        process_video_background,
        task_id,
        request.start_from,
        request.enable_multimodal,
        request.keep_temp
    )

    # 更新状态
    task_manager.update_status(task_id, "processing", "starting", 0.1)

    return {"message": "处理已开始", "task_id": task_id}

@app.get("/api/status/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    try:
        metadata = task_manager.load_metadata(task_id)
        return metadata
    except:
        raise HTTPException(status_code=404, detail="任务不存在")

@app.get("/api/results/{task_id}")
async def get_results(task_id: str):
    """获取处理结果"""
    try:
        metadata = task_manager.load_metadata(task_id)
    except:
        raise HTTPException(status_code=404, detail="任务不存在")

    if metadata["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")

    task_dir = task_manager.get_task_dir(task_id)
    results = {}

    # 收集所有结果文件
    result_files = {
        "asr_result": "asr_result.json",
        "merged_text": "merged_text.json",
        "summary": "summary.json",
        "multimodal_notes": "multimodal_notes.json"
    }

    for key, filename in result_files.items():
        file_path = task_dir / filename
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                results[key] = json.load(f)

    return {
        "task_id": task_id,
        "status": metadata["status"],
        "results": results
    }

@app.get("/api/export/{task_id}/markdown")
async def export_markdown(task_id: str):
    """导出 Markdown 格式笔记"""
    try:
        metadata = task_manager.load_metadata(task_id)
    except:
        raise HTTPException(status_code=404, detail="任务不存在")

    if metadata["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")

    task_dir = task_manager.get_task_dir(task_id)
    # 图文笔记文件可能在两个位置之一
    notes_file = task_dir / "multimodal_notes" / "multimodal_notes.json"
    if not notes_file.exists():
        notes_file = task_dir / "multimodal_notes.json"

    if not notes_file.exists():
        raise HTTPException(status_code=404, detail="图文笔记文件不存在")

    # 生成 Markdown
    generator = MultimodalNoteGenerator(
        jina_api_key=os.getenv("JINA_API_KEY", "dummy")
    )

    markdown_file = task_dir / "notes.md"
    # 传递图片基础路径，确保相对路径计算正确
    generator.export_to_markdown(
        notes_json_path=str(notes_file),
        output_path=str(markdown_file),
        image_base_path=str(task_dir)
    )

    return FileResponse(
        path=str(markdown_file),
        filename=f"video_notes_{task_id}.md",
        media_type="text/markdown"
    )


@app.get("/api/export/{task_id}/json")
async def export_json(task_id: str):
    """导出原始 JSON 格式笔记"""
    try:
        metadata = task_manager.load_metadata(task_id)
    except:
        raise HTTPException(status_code=404, detail="任务不存在")

    if metadata["status"] != "completed":
        raise HTTPException(status_code=400, detail="任务尚未完成")

    task_dir = task_manager.get_task_dir(task_id)
    # 图文笔记文件可能在两个位置之一
    notes_file = task_dir / "multimodal_notes" / "multimodal_notes.json"
    if not notes_file.exists():
        notes_file = task_dir / "multimodal_notes.json"

    if not notes_file.exists():
        raise HTTPException(status_code=404, detail="图文笔记文件不存在")

    return FileResponse(
        path=str(notes_file),
        filename=f"video_notes_{task_id}.json",
        media_type="application/json"
    )


# 全局任务管理器
task_manager = TaskManager()


async def process_video_background(task_id: str, start_from: str, enable_multimodal: bool, keep_temp: bool):
    """后台处理视频的函数"""
    try:
        task_dir = task_manager.get_task_dir(task_id)
        video_path = task_dir / "original_video.mp4"

        # 创建工作流实例
        workflow = VideoProcessingWorkflow(enable_multimodal=enable_multimodal)

        # 更新进度回调
        def update_progress(step: str, progress: float):
            logger.info(f"🔄 进度更新: {step} - {progress:.1%}")
            task_manager.update_status(task_id, "processing", step, progress)

        # 执行处理
        result = workflow.process_video(
            video_path=str(video_path),
            output_dir=str(task_dir),
            keep_temp=keep_temp,
            start_from=start_from,
            progress_callback=update_progress
        )

        # 处理完成
        task_manager.update_status(task_id, "completed", "finished", 1.0)

    except Exception as e:
        # 处理失败
        task_manager.update_status(task_id, "failed", error_message=str(e))

# 启动服务器的代码
if __name__ == "__main__":
    import uvicorn

    # 确保存储目录存在
    storage_dir = Path("storage")
    storage_dir.mkdir(exist_ok=True)

    logger.info("🚀 启动视频处理 API 服务...")
    logger.info(f"📁 存储目录: {storage_dir.absolute()}")
    logger.info("🌐 API 文档: http://localhost:8000/docs")
    logger.info("🔍 健康检查: http://localhost:8000/api/health")
    logger.info("📤 上传接口: http://localhost:8000/api/upload")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
