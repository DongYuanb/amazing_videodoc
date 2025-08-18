"""处理相关路由"""
import json
from fastapi import APIRouter, HTTPException, BackgroundTasks
from models.api_models import ProcessRequest
from services.task_manager import TaskManager
from services.video_processor import VideoProcessingWorkflow
from task_logger import TaskLogger

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
    task_manager.update_status(task_id, "processing", "starting")

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


async def process_video_background(task_id: str, enable_multimodal: bool, keep_temp: bool):
    """后台处理视频的函数"""
    task_logger = None
    try:
        task_dir = task_manager.get_task_dir(task_id)
        video_path = task_dir / "original_video.mp4"

        # 获取任务专用logger
        task_logger = TaskLogger.get_logger(task_id, str(task_dir))

        # 创建工作流实例
        workflow = VideoProcessingWorkflow(enable_multimodal=enable_multimodal, task_logger=task_logger)

        # 执行处理
        result = workflow.process_video(
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
