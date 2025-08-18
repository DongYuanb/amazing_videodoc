"""API数据模型"""
from typing import Optional
from pydantic import BaseModel


class TaskStatus(BaseModel):
    task_id: str
    status: str  # pending, processing, completed, failed
    created_at: str
    updated_at: str
    error_message: Optional[str] = None


class ProcessRequest(BaseModel):
    enable_multimodal: bool = True
    keep_temp: bool = False
