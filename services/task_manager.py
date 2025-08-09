"""任务管理服务"""
import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict
from fastapi import HTTPException

from task_logger import TaskLogger, create_task_logger


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
        
        # 创建任务专用logger
        task_logger = create_task_logger(task_id, str(task_dir))
        task_logger.info(f"任务创建成功 - 原始文件名: {original_filename}")

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

        # 记录状态更新到任务日志
        if task_id in TaskLogger._loggers:
            task_logger = TaskLogger._loggers[task_id]
            if error_message:
                task_logger.error(f"任务状态更新: {status} - {error_message}")
            else:
                task_logger.info(f"任务状态更新: {status} - {current_step or ''} ({progress or 0:.1%})")

    def validate_task_completed(self, task_id: str) -> dict:
        """验证任务是否完成并返回元数据"""
        metadata = self.load_metadata(task_id)
        if metadata["status"] != "completed":
            raise HTTPException(status_code=400, detail="任务尚未完成")
        return metadata
