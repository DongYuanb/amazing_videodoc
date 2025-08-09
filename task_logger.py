"""
任务日志记录模块，用于跟踪和记录处理任务的执行过程
"""
import logging
import time
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

class TaskLogger:
    """任务日志记录器，跟踪任务执行过程中的步骤和进度"""
    
    def __init__(self, task_id: str, log_dir: str = "logs"):
        """
        初始化任务日志记录器
        
        Args:
            task_id: 任务ID
            log_dir: 日志存储目录
        """
        self.task_id = task_id
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 为每个任务创建单独的日志文件
        self.log_file = self.log_dir / f"task_{task_id}.log"
        
        # 配置日志
        self.logger = logging.getLogger(f"task_{task_id}")
        self.logger.setLevel(logging.INFO)
        
        # 文件处理器
        file_handler = logging.FileHandler(self.log_file)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 任务状态
        self.start_time = time.time()
        self.current_step = None
        self.progress = 0.0
        self.steps_completed = []
        
        self.logger.info(f"任务 {task_id} 开始记录")
    
    def log_step(self, step_name: str, progress: float, message: Optional[str] = None):
        """
        记录任务步骤
        
        Args:
            step_name: 步骤名称
            progress: 当前进度 (0.0 到 1.0)
            message: 可选消息
        """
        self.current_step = step_name
        self.progress = progress
        
        log_message = f"步骤: {step_name} - 进度: {progress:.1%}"
        if message:
            log_message += f" - {message}"
        
        self.logger.info(log_message)
    
    def log_error(self, error_message: str, step_name: Optional[str] = None):
        """
        记录错误
        
        Args:
            error_message: 错误消息
            step_name: 可选步骤名称
        """
        if step_name:
            self.logger.error(f"错误 [{step_name}]: {error_message}")
        else:
            self.logger.error(f"错误: {error_message}")
    
    def complete_step(self, step_name: str):
        """
        标记步骤完成
        
        Args:
            step_name: 步骤名称
        """
        self.steps_completed.append(step_name)
        self.logger.info(f"步骤完成: {step_name}")
    
    def complete_task(self, success: bool = True, message: Optional[str] = None):
        """
        完成任务
        
        Args:
            success: 任务是否成功
            message: 可选消息
        """
        elapsed_time = time.time() - self.start_time
        if success:
            self.progress = 1.0
            status = "成功"
        else:
            status = "失败"
        
        log_message = f"任务 {self.task_id} {status}完成，用时: {elapsed_time:.2f}秒"
        if message:
            log_message += f" - {message}"
        
        self.logger.info(log_message)
    
    def get_task_status(self) -> Dict[str, Any]:
        """
        获取任务状态
        
        Returns:
            任务状态字典
        """
        return {
            "task_id": self.task_id,
            "current_step": self.current_step,
            "progress": self.progress,
            "steps_completed": self.steps_completed,
            "elapsed_time": time.time() - self.start_time,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat()
        }
    
    def close(self):
        """关闭日志处理器"""
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)
        self.logger.info(f"任务 {self.task_id} 日志关闭")


# 全局任务日志记录器字典
_task_loggers: Dict[str, TaskLogger] = {}

def create_task_logger(task_id: str, log_dir: str = "logs") -> TaskLogger:
    """
    创建任务日志记录器
    
    Args:
        task_id: 任务ID
        log_dir: 日志存储目录
    
    Returns:
        TaskLogger实例
    """
    if task_id in _task_loggers:
        return _task_loggers[task_id]
    
    logger = TaskLogger(task_id, log_dir)
    _task_loggers[task_id] = logger
    return logger

def get_task_logger(task_id: str) -> Optional[TaskLogger]:
    """
    获取任务日志记录器
    
    Args:
        task_id: 任务ID
    
    Returns:
        TaskLogger实例或None
    """
    return _task_loggers.get(task_id)

def close_task_logger(task_id: str):
    """
    关闭任务日志记录器
    
    Args:
        task_id: 任务ID
    """
    if task_id in _task_loggers:
        _task_loggers[task_id].close()
        del _task_loggers[task_id]
