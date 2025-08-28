"""处理相关路由"""
import json
import os
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from models.api_models import ProcessRequest
from services.task_manager import TaskManager
from services.video_processor import VideoProcessingWorkflow
from services.summary_generator import Summarizer
from utils.task_logger import TaskLogger

router = APIRouter(prefix="/api", tags=["process"])

# 全局任务管理器实例
task_manager = TaskManager()


@router.post("/process/{task_id}")
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
    task_manager.update_status(task_id, "processing")

    return {"message": "处理已开始", "task_id": task_id}


@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    try:
        metadata = task_manager.load_metadata(task_id)
        return metadata
    except:
        raise HTTPException(status_code=404, detail="任务不存在")


@router.get("/results/{task_id}")
async def get_results(task_id: str):
    """获取处理结果"""
    metadata = task_manager.validate_task_completed(task_id)
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
        alt_path = None
        # 针对 multimodal_notes，优先兼容嵌套目录
        if key == "multimodal_notes" and not file_path.exists():
            alt_path = task_dir / "multimodal_notes" / "multimodal_notes.json"
        target_path = file_path if file_path.exists() else alt_path
        if target_path and target_path.exists():
            with open(target_path, "r", encoding="utf-8") as f:
                results[key] = json.load(f)

    return {
        "task_id": task_id,
        "status": metadata["status"],
        "results": results
    }


@router.get("/results/{task_id}/asr")
async def get_asr_result(task_id: str):
    """返回 ASR 转录数据"""
    try:
        task_manager.load_metadata(task_id)
        task_dir = task_manager.get_task_dir(task_id)
        asr_file = task_dir / "asr_result.json"
        if not asr_file.exists():
            raise HTTPException(status_code=404, detail="ASR 转录尚未生成")
        with open(asr_file, "r", encoding="utf-8") as f:
            return {"task_id": task_id, "data": json.load(f)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取 ASR 失败: {str(e)}")


@router.get("/stream-summary/{task_id}")
async def stream_full_summary(task_id: str):
    """流式生成视频全文摘要"""
    try:
        # 验证任务存在
        task_manager.load_metadata(task_id)
        task_dir = task_manager.get_task_dir(task_id)
        asr_file = task_dir / "asr_result.json"

        # 检查ASR文件是否存在
        if not asr_file.exists():
            raise HTTPException(status_code=404, detail="ASR转录文件不存在，请等待转录完成")

        # 创建摘要生成器
        model_id = os.getenv("MODEL_ID", "gpt-3.5-turbo")
        summarizer = Summarizer(model_id)

        # 返回流式响应
        return StreamingResponse(
            summarizer.generate_full_summary_stream(str(asr_file)),
            media_type="text/plain; charset=utf-8",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # 禁用nginx缓冲
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成摘要失败: {str(e)}")


async def process_video_background(task_id: str, enable_multimodal: bool, keep_temp: bool):
    """后台处理视频的函数"""
    task_logger = None
    try:
        task_dir = task_manager.get_task_dir(task_id)
        video_path = task_dir / "original_video.mp4"

        # 获取任务专用logger
        task_logger = TaskLogger.get_logger(task_id, str(task_dir))

        # 创建工作流实例
        workflow = VideoProcessingWorkflow(enable_multimodal=enable_multimodal, task_logger=task_logger, task_manager=task_manager, task_id=task_id)

        # 执行处理
        result = await run_in_threadpool(
            workflow.process_video,
            video_path=str(video_path),
            output_dir=str(task_dir),
            keep_temp=keep_temp
        )

        # 处理完成
        task_logger.info("任务处理完成！")
        task_logger.info(f"处理结果: {result}")
        task_manager.update_status(task_id, "completed")

    except Exception as e:
        # 处理失败
        if task_logger:
            task_logger.error(f"任务处理失败: {e}")
        task_manager.update_status(task_id, "failed", error_message=str(e))

    finally:
        pass
