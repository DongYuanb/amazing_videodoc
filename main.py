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
from typing import Optional, Dict
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
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
    enable_multimodal: bool = True
    keep_temp: bool = False

# 任务管理器
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
    """视频处理工作流程"""

    def __init__(self, enable_multimodal: bool = True):
        self.enable_multimodal = enable_multimodal
        self._init_services()

    def _init_services(self):
        """初始化所有服务"""
        model_id = os.getenv("MODEL_ID", "openai/gpt-oss-20b:free")

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
        jina_api_key = os.getenv("JINA_API_KEY")
        if not jina_api_key:
            logger.warning("未提供 Jina API Key，跳过图文笔记生成")
            return None

        try:
            return MultimodalNoteGenerator(
                jina_api_key=jina_api_key,
                ffmpeg_path=os.getenv("FFMPEG_PATH", "ffmpeg")
            )
        except Exception as e:
            logger.error(f"图文笔记生成器初始化失败: {e}")
            return None

    def process_video(self, video_path: str, output_dir: str, keep_temp: bool = False, progress_callback=None) -> Dict[str, str]:
        """处理视频的完整流程"""
        os.makedirs(output_dir, exist_ok=True)

        logger.info(f"开始处理视频: {video_path}")
        logger.info(f"输出目录: {output_dir}")

        # 定义文件路径
        audio_path = os.path.join(output_dir, "audio.wav")
        asr_json = os.path.join(output_dir, "asr_result.json")
        merged_json = os.path.join(output_dir, "merged_text.json")
        summary_json = os.path.join(output_dir, "summary.json")
        multimodal_notes = None

        try:
            # 1. 提取音频
            logger.info("1️⃣ 提取音频...")
            if progress_callback:
                progress_callback("audio_extract", 0.1)
            extract_audio_for_asr(video_path, audio_path)

            # 2. ASR转录
            logger.info("2️⃣ ASR转录...")
            if progress_callback:
                progress_callback("asr", 0.2)
                self.asr_service.transcribe_audio_with_progress(audio_path, asr_json, progress_callback)
            else:
                self.asr_service.transcribe_audio(audio_path, asr_json)

            # 3. 文本合并
            logger.info("3️⃣ 文本合并...")
            if progress_callback:
                progress_callback("text_merge", 0.6)
                success = self.text_merger.process_file_with_progress(asr_json, merged_json, progress_callback)
            else:
                success = self.text_merger.process_file(asr_json, merged_json)
            if not success:
                raise RuntimeError("文本合并失败")

            # 4. 生成摘要
            logger.info("4️⃣ 生成摘要...")
            if progress_callback:
                progress_callback("summary", 0.8)
                success = self.summary_generator.process_file_with_progress(merged_json, summary_json, progress_callback)
            else:
                success = self.summary_generator.process_file(merged_json, summary_json)
            if not success:
                raise RuntimeError("摘要生成失败")

            # 5. 生成图文笔记（可选）
            if self.enable_multimodal and self.multimodal_generator:
                logger.info("5️⃣ 生成图文笔记...")
                if progress_callback:
                    progress_callback("multimodal", 0.9)
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
                    logger.info("清理临时音频文件")
                except:
                    pass

            if progress_callback:
                progress_callback("completed", 1.0)

            logger.info("✅ 处理完成！")
            return {
                "video_path": video_path,
                "output_dir": output_dir,
                "asr_result": asr_json,
                "merged_text": merged_json,
                "summary": summary_json,
                "multimodal_notes": multimodal_notes
            }

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 或指定你的前端地址，如 ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


async def process_video_background(task_id: str, enable_multimodal: bool, keep_temp: bool):
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
