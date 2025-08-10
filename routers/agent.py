from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import JSONResponse
import logging
from agno.agent import Agent
from agno.models.openai import OpenAIChat

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(prefix="/api/agent", tags=["agent"])

# 初始化 agent
basic_agent = Agent(
    name="Basic Agent",
    agent_id="basic_agent",
    model=OpenAIChat(id="gpt-4o"), 
    add_history_to_messages=True,
    num_history_responses=3,
    add_datetime_to_instructions=True,
    markdown=True,
)

@router.post("/runs")
async def run_agent(
    message: str = Form(...),
    agent_id: str = Form(default="basic_agent")
):
    """
    运行 agent 并返回响应
    
    Args:
        message: 用户消息
        agent_id: agent ID (默认: basic_agent)
    
    Returns:
        JSON 响应包含 agent 的回复
    """
    try:
        logger.info(f"收到 agent 请求: agent_id={agent_id}, message={message[:100]}...")
        
        # 验证 agent_id
        if agent_id != "basic_agent":
            raise HTTPException(status_code=400, detail=f"不支持的 agent_id: {agent_id}")
        
        # 运行 agent
        response = basic_agent.run(message)
        
        logger.info(f"Agent 响应成功: {len(response.content)} 字符")
        
        return JSONResponse(content={
            "content": response.content,
            "agent_id": agent_id,
            "status": "success"
        })
        
    except Exception as e:
        logger.error(f"Agent 运行失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Agent 运行失败: {str(e)}")



