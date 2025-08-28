"""任务管理服务"""
import json
import uuid
from pathlib import Path
from datetime import datetime
from fastapi import HTTPException

from utils.task_logger import TaskLogger, create_task_logger


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
            "current_step": "pending",
            "progress_percent": 0.0,
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

    def update_status(self, task_id: str, status: str, error_message: str = None):
        """更新任务状态"""
        metadata = self.load_metadata(task_id)
        metadata["status"] = status
        # 状态与步骤的关系（完成/失败时更新步骤）
        if status == "completed":
            metadata["current_step"] = "completed"
            metadata["progress_percent"] = 1.0
        elif status == "failed":
            metadata["current_step"] = "failed"
        metadata["updated_at"] = datetime.now().isoformat()

        if error_message is not None:
            metadata["error_message"] = error_message

        self.save_metadata(task_id, metadata)

        # 记录状态更新到任务日志
        if task_id in TaskLogger._loggers:
            task_logger = TaskLogger._loggers[task_id]
            if error_message:
                task_logger.error(f"任务状态更新: {status} - {error_message}")
            else:
                task_logger.info(f"任务状态更新: {status}")

    # ---- 进度相关辅助 ----
    _STEP_ORDER = ["extract_audio","asr","merge_text","summary","multimodal"]
    _STEP_WEIGHTS = {"extract_audio":0.10,"asr":0.20,"merge_text":0.2,"summary":0.2,"multimodal":0.30}

    def _cumulative_weight(self, step: str) -> float:
        total = 0.0
        for s in self._STEP_ORDER:
            total += self._STEP_WEIGHTS.get(s,0.0)
            if s == step:
                break
        return min(total, 1.0)

    def update_step(self, task_id: str, step: str):
        """更新当前步骤到边界并写入累计进度"""
        md = self.load_metadata(task_id)
        md["current_step"] = step
        md["progress_percent"] = self._cumulative_weight(step)
        md["updated_at"] = datetime.now().isoformat()
        self.save_metadata(task_id, md)

    def update_progress(self, task_id: str, step: str, fraction: float | None = None):
        """更新当前步骤与进度；fraction为当前步骤内的比例(0-1)"""
        md = self.load_metadata(task_id)
        md["current_step"] = step
        if fraction is None:
            md["progress_percent"] = self._cumulative_weight(step)
        else:
            prev = 0.0
            for s in self._STEP_ORDER:
                if s == step:
                    break
                prev += self._STEP_WEIGHTS.get(s,0.0)
            md["progress_percent"] = max(0.0, min(1.0, prev + self._STEP_WEIGHTS.get(step,0.0)*max(0.0,min(1.0,fraction))))
        md["updated_at"] = datetime.now().isoformat()
        self.save_metadata(task_id, md)

    def validate_task_completed(self, task_id: str) -> dict:
        """验证任务是否完成并返回元数据"""
        metadata = self.load_metadata(task_id)
        if metadata["status"] != "completed":
            raise HTTPException(status_code=400, detail="任务尚未完成")
        return metadata
