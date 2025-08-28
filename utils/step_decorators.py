#!/usr/bin/env python3
"""
Step decorators/utilities for workflow steps: logging, timing, exception handling, progress update.
Use step_decorator(name, task_manager, task_id, logger) to wrap a callable.
"""
from __future__ import annotations
import time
from typing import Any, Callable

def step_decorator(name:str, task_manager=None, task_id:str|None=None, logger=None, update_progress:bool=True)->Callable[[Callable[...,Any]],Callable[...,Any]]:
    """Decorator factory: wraps fn with logging/timing, updates progress on success, logs on failure.
    Args: name: step name; task_manager: TaskManager-like; task_id: str; logger: Logger.
    """
    def deco(fn:Callable[...,Any])->Callable[...,Any]:
        def wrapper(*a,**k):
            t=time.time()
            if logger: logger.info(f"开始步骤: {name}")
            try:
                r=fn(*a,**k)
                if update_progress and task_manager and task_id:
                    try: task_manager.update_step(task_id,name)
                    except Exception as _:
                        if logger: logger.warning(f"进度更新失败: {name}")
                if logger: logger.info(f"完成步骤: {name} 用时 {time.time()-t:.2f}s")
                return r
            except Exception as e:
                if logger: logger.error(f"步骤失败: {name} - {e}")
                # 不在此处改变最终状态(由上层决定)，仅记录错误；如需直接标记失败，可在参数层扩展
                raise
        return wrapper
    return deco

def run_step(name:str, fn:Callable[...,Any], *a, task_manager=None, task_id:str|None=None, logger=None, update_progress:bool=True, **k)->Any:
    """Helper to call functions with the same behavior without decorator syntax."""
    return step_decorator(name,task_manager,task_id,logger,update_progress)(fn)(*a,**k)

