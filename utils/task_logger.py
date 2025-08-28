#!/usr/bin/env python3
"""
任务日志管理器 - 为每个任务创建独立的日志文件
"""
import os
import logging
from pathlib import Path
from typing import Dict, Optional


class TaskLogger:
    """任务日志管理器 - 为每个任务创建独立的logger"""
    
    _loggers: Dict[str, logging.Logger] = {}
    _handlers: Dict[str, logging.FileHandler] = {}
    
    @classmethod
    def get_logger(cls, task_id: str, task_dir: str = None) -> logging.Logger:
        """
        获取或创建任务专用的logger
        """
        if task_id in cls._loggers:
            return cls._loggers[task_id]
        
        # 创建logger
        logger = logging.getLogger(f"task_{task_id}")
        logger.setLevel(logging.DEBUG)
        
        # 避免重复添加handler
        if logger.handlers:
            logger.handlers.clear()
        
        # 确定日志文件路径
        if task_dir is None:
            task_dir = f"storage/tasks/{task_id}"
        
        log_dir = Path(task_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "processing.log"
        
        # 创建文件handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        # 创建控制台handler（可选，用于调试）
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 设置格式
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加handlers
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # 缓存logger和handler
        cls._loggers[task_id] = logger
        cls._handlers[task_id] = file_handler
        
        logger.info(f"任务日志初始化完成 - 任务ID: {task_id}")
        logger.info(f"日志文件: {log_file}")
        
        return logger
    
    @classmethod
    def close_logger(cls, task_id: str):
        """
        关闭并清理任务logger
        """
        if task_id in cls._loggers:
            logger = cls._loggers[task_id]
            
            # 记录关闭信息
            logger.info(f"任务日志关闭 - 任务ID: {task_id}")
            
            # 关闭所有handlers
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
            
            # 从缓存中移除
            del cls._loggers[task_id]
            
            if task_id in cls._handlers:
                del cls._handlers[task_id]
    
    @classmethod
    def cleanup_all(cls):
        """清理所有logger"""
        for task_id in list(cls._loggers.keys()):
            cls.close_logger(task_id)


class LoggerMixin:
    """日志混入类 - 为其他类提供日志功能"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger: Optional[logging.Logger] = None
        self.task_id: Optional[str] = None
    
    def set_logger(self, logger: logging.Logger, task_id: str = None):
        """设置logger"""
        self.logger = logger
        self.task_id = task_id
    
    def log_info(self, message: str):
        """记录信息日志"""
        if self.logger:
            self.logger.info(message)
        else:
            print(f"INFO: {message}")
    
    def log_warning(self, message: str):
        """记录警告日志"""
        if self.logger:
            self.logger.warning(message)
        else:
            print(f"WARNING: {message}")
    
    def log_error(self, message: str):
        """记录错误日志"""
        if self.logger:
            self.logger.error(message)
        else:
            print(f"ERROR: {message}")
    
    def log_debug(self, message: str):
        """记录调试日志"""
        if self.logger:
            self.logger.debug(message)
        else:
            print(f"DEBUG: {message}")


# 便捷函数
def create_task_logger(task_id: str, task_dir: str = None) -> logging.Logger:
    """便捷函数：创建任务logger"""
    return TaskLogger.get_logger(task_id, task_dir)


def close_task_logger(task_id: str):
    """便捷函数：关闭任务logger"""
    TaskLogger.close_logger(task_id)
