"""Agent路由 - API接口层"""
from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import JSONResponse
import logging
from services.agent import video_notes_agent_service

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/agent", tags=["agent"])

@router.post("/runs")
async def run_agent(
    message: str = Form(...),
    task_id: str = Form(...),
    user_id: str = Form(default="user")
):
    """
    运行 agent 并返回响应
    """
    try:
        logger.info(f"收到 agent 请求: task_id={task_id}, user_id={user_id}, message={message[:100]}...")

        # 调用服务层运行agent
        response_content = video_notes_agent_service.run_agent(task_id, message, user_id)

        logger.info(f"Agent 响应成功: task_id={task_id}, user_id={user_id}, {len(response_content)} 字符")

        return JSONResponse(content={
            "content": response_content,
            "task_id": task_id,
            "user_id": user_id,
            "status": "success"
        })

    except Exception as e:
        logger.error(f"Agent 运行失败: task_id={task_id}, user_id={user_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Agent 运行失败: {str(e)}")

@router.delete("/sessions/{task_id}")
async def clear_agent_session(task_id: str, user_id: str = "user"):
    """
    清除指定task_id的agent会话
    """
    try:
        success = video_notes_agent_service.clear_session(task_id, user_id)

        if success:
            logger.info(f"已清除task_id {task_id}, user_id {user_id} 的agent会话")
            return {"message": f"已清除task_id {task_id} 的会话", "status": "success"}
        else:
            return {"message": f"task_id {task_id} 的会话不存在", "status": "not_found"}
    except Exception as e:
        logger.error(f"清除会话失败: task_id={task_id}, user_id={user_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"清除会话失败: {str(e)}")


@router.post("/knowledge/reload/{task_id}")
async def reload_knowledge(task_id: str):
    """
    重新加载指定task_id的知识库（当笔记更新时调用）
    """
    try:
        success = video_notes_agent_service.reload_knowledge(task_id)

        if success:
            logger.info(f"已重新加载task_id {task_id} 的知识库")
            return {"message": f"已重新加载task_id {task_id} 的知识库", "status": "success"}
        else:
            return {"message": f"重新加载task_id {task_id} 的知识库失败", "status": "error"}

    except Exception as e:
        logger.error(f"重新加载知识库失败: task_id={task_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"重新加载知识库失败: {str(e)}")

from fastapi.responses import StreamingResponse

@router.post("/stream")
async def run_agent_stream(message: str = Form(...), task_id: str = Form(...), user_id: str = Form(default="user")):
    gen = video_notes_agent_service.stream_agent(task_id, message, user_id)
    return StreamingResponse(gen, media_type="text/event-stream", headers={"Cache-Control":"no-cache","Connection":"keep-alive","X-Accel-Buffering":"no"})

