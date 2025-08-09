"""上传相关路由"""
import shutil
from fastapi import APIRouter, UploadFile, File, HTTPException
from services.task_manager import TaskManager

router = APIRouter(prefix="/api", tags=["upload"])

# 全局任务管理器实例
task_manager = TaskManager()


@router.post("/upload")
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


@router.get("/static-info/{task_id}")
async def static_info(task_id: str):
    """返回前端静态资源的路径信息"""
    return {
        "video": f"/storage/tasks/{task_id}/original_video.mp4",
        "notes_json": [
            f"/storage/tasks/{task_id}/multimodal_notes.json",
            f"/storage/tasks/{task_id}/multimodal_notes/multimodal_notes.json"
        ],
        "frames_base": f"/storage/tasks/{task_id}/multimodal_notes/frames"
    }
