from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import JSONResponse
import logging
from typing import Dict
from agno.agent import Agent
from agno.models.openai import OpenAIChat

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/agent", tags=["agent"])

# 存储每个task_id对应的agent实例
agent_sessions: Dict[str, Agent] = {}

def get_or_create_agent(task_id: str) -> Agent:
    """获取或创建指定task_id的agent实例"""
    if task_id not in agent_sessions:
        agent_sessions[task_id] = Agent(
            name=f"Agent-{task_id}",
            agent_id=f"agent_{task_id}",
            model=OpenAIChat(id="gpt-4o"),
            add_history_to_messages=True,
            num_history_responses=3,
            add_datetime_to_instructions=True,
            markdown=True,
        )
        logger.info(f"为task_id {task_id} 创建新的agent实例")
    return agent_sessions[task_id]

@router.post("/runs")
async def run_agent(
    message: str = Form(...),
    task_id: str = Form(...)
):
    """
    运行 agent 并返回响应

    Args:
        message: 用户消息
        task_id: 任务ID，用于会话隔离

    Returns:
        JSON 响应包含 agent 的回复
    """
    try:
        logger.info(f"收到 agent 请求: task_id={task_id}, message={message[:100]}...")

        # 获取或创建该task_id对应的agent
        agent = get_or_create_agent(task_id)

        # 运行 agent
        response = agent.run(message)

        logger.info(f"Agent 响应成功: task_id={task_id}, {len(response.content)} 字符")

        return JSONResponse(content={
            "content": response.content,
            "task_id": task_id,
            "status": "success"
        })

    except Exception as e:
        logger.error(f"Agent 运行失败: task_id={task_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"Agent 运行失败: {str(e)}")

@router.delete("/sessions/{task_id}")
async def clear_agent_session(task_id: str):
    """
    清除指定task_id的agent会话

    Args:
        task_id: 任务ID

    Returns:
        清除结果
    """
    try:
        if task_id in agent_sessions:
            del agent_sessions[task_id]
            logger.info(f"已清除task_id {task_id} 的agent会话")
            return {"message": f"已清除task_id {task_id} 的会话", "status": "success"}
        else:
            return {"message": f"task_id {task_id} 的会话不存在", "status": "not_found"}
    except Exception as e:
        logger.error(f"清除会话失败: task_id={task_id}, error={str(e)}")
        raise HTTPException(status_code=500, detail=f"清除会话失败: {str(e)}")



