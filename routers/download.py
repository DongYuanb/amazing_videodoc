"""在线视频下载相关路由"""
import os
import shutil
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from models.download_models import DownloadUrlRequest, DownloadStatus, Platform
from services.task_manager import TaskManager
from services.platform_detector import PlatformDetector
from services.video_downloader import VideoDownloaderService
from services.video_processor import VideoProcessingWorkflow
from task_logger import TaskLogger

router = APIRouter(prefix="/api", tags=["download"])

# 全局服务实例
task_manager = TaskManager()
platform_detector = PlatformDetector()
downloader_service = VideoDownloaderService()


@router.post("/download-url")
async def download_from_url(request: DownloadUrlRequest, background_tasks: BackgroundTasks):
    """
    从在线视频URL下载并处理视频
    
    Args:
        request: 包含视频URL和下载参数的请求
        background_tasks: FastAPI后台任务
        
    Returns:
        任务ID和基本信息
    """
    # 1. 平台检测
    if request.platform:
        platform = request.platform
    else:
        platform = platform_detector.detect_platform(request.url)
        if not platform:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的视频平台。支持的平台: {platform_detector.get_supported_platforms()}"
            )
    
    # 2. 检查平台支持
    if not downloader_service.is_platform_supported(platform):
        raise HTTPException(
            status_code=400,
            detail=f"平台 {platform} 暂未支持，目前支持: YouTube, Bilibili"
        )
    
    # 3. 获取视频基本信息
    try:
        video_info = downloader_service.get_video_info(request.url, platform)
        video_title = video_info.get("title", "Unknown Video")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无法获取视频信息: {str(e)}")
    
    # 4. 创建任务
    task_id = task_manager.create_task(f"{platform}_{video_title}")
    
    # 5. 启动后台下载和处理
    background_tasks.add_task(
        download_and_process_video,
        task_id,
        request.url,
        platform,
        request.quality,
        video_info
    )
    
    # 6. 更新初始状态
    task_manager.update_status(task_id, "downloading")
    
    return {
        "task_id": task_id,
        "platform": platform.value,
        "title": video_title,
        "message": "视频下载已开始",
        "estimated_duration": video_info.get("duration", 0)
    }


@router.get("/download-status/{task_id}")
async def get_download_status(task_id: str):
    """获取下载任务状态"""
    try:
        metadata = task_manager.load_metadata(task_id)
        return DownloadStatus(
            task_id=task_id,
            status=metadata["status"],
            platform=metadata.get("platform"),
            title=metadata.get("title"),
            error_message=metadata.get("error_message")
        )
    except:
        raise HTTPException(status_code=404, detail="任务不存在")


@router.get("/supported-platforms")
async def get_supported_platforms():
    """获取支持的视频平台列表"""
    return {
        "platforms": [
            {
                "name": "YouTube",
                "value": "youtube",
                "supported": True,
                "description": "支持YouTube视频下载"
            },
            {
                "name": "Bilibili",
                "value": "bilibili", 
                "supported": True,
                "description": "支持B站视频下载"
            },
            {
                "name": "抖音",
                "value": "douyin",
                "supported": False,
                "description": "即将支持"
            },
            {
                "name": "TikTok",
                "value": "tiktok",
                "supported": False,
                "description": "即将支持"
            }
        ]
    }


@router.post("/preview-video")
async def preview_video_info(request: DownloadUrlRequest):
    """预览视频信息（不下载）"""
    # 平台检测
    if request.platform:
        platform = request.platform
    else:
        platform = platform_detector.detect_platform(request.url)
        if not platform:
            raise HTTPException(
                status_code=400,
                detail="无法识别视频平台"
            )
    
    # 检查平台支持
    if not downloader_service.is_platform_supported(platform):
        raise HTTPException(
            status_code=400,
            detail=f"平台 {platform} 暂未支持"
        )
    
    # 获取视频信息
    try:
        video_info = downloader_service.get_video_info(request.url, platform)
        return {
            "platform": platform.value,
            "title": video_info.get("title"),
            "duration": video_info.get("duration"),
            "thumbnail": video_info.get("thumbnail"),
            "uploader": video_info.get("uploader"),
            "view_count": video_info.get("view_count")
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"获取视频信息失败: {str(e)}")


async def download_and_process_video(task_id: str, url: str, platform: Platform, 
                                   quality, video_info: dict):
    """后台下载和处理视频"""
    task_logger = None
    try:
        task_dir = task_manager.get_task_dir(task_id)
        task_logger = TaskLogger.get_logger(task_id, str(task_dir))
        
        # 更新任务元数据
        metadata = task_manager.load_metadata(task_id)
        metadata.update({
            "platform": platform.value,
            "title": video_info.get("title", "Unknown"),
            "url": url
        })
        task_manager.save_metadata(task_id, metadata)
        
        # 1. 下载视频
        task_logger.info(f"开始下载 {platform} 视频: {url}")
        task_manager.update_status(task_id, "downloading", "downloading_video", 0.2)
        
        download_result = downloader_service.download_video(
            url, platform, str(task_dir), quality
        )
        
        # 2. 重命名为标准格式
        original_video_path = task_dir / "original_video.mp4"
        shutil.move(download_result.file_path, original_video_path)
        
        task_logger.info(f"视频下载完成: {download_result.title}")
        task_manager.update_status(task_id, "processing")

        # 3. 启动视频处理工作流
        workflow = VideoProcessingWorkflow(enable_multimodal=True, task_logger=task_logger)

        # 执行处理
        workflow.process_video(
            video_path=str(original_video_path),
            output_dir=str(task_dir),
            keep_temp=False
        )

        # 处理完成
        task_logger.info("视频处理完成！")
        task_manager.update_status(task_id, "completed")
        
    except Exception as e:
        if task_logger:
            task_logger.error(f"下载或处理失败: {e}")
        task_manager.update_status(task_id, "failed", error_message=str(e))
    
    finally:
        pass
