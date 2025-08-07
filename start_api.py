#!/usr/bin/env python3
"""
启动 FastAPI 服务的脚本
"""
import sys
from pathlib import Path

# 检查 FastAPI 是否安装
try:
    import uvicorn
    from main import FASTAPI_AVAILABLE, app
except ImportError:
    print("❌ 请先安装 FastAPI 相关依赖:")
    print("pip install fastapi uvicorn python-multipart")
    sys.exit(1)

if not FASTAPI_AVAILABLE:
    print("❌ FastAPI 不可用，请检查安装")
    sys.exit(1)

if __name__ == "__main__":
    # 确保存储目录存在
    storage_dir = Path("storage")
    storage_dir.mkdir(exist_ok=True)
    
    print("🚀 启动视频处理 API 服务...")
    print("📁 存储目录:", storage_dir.absolute())
    print("🌐 API 文档: http://localhost:8000/docs")
    print("🔍 健康检查: http://localhost:8000/api/health")
    print("📤 上传接口: http://localhost:8000/api/upload")
    
    # 启动服务
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
