#!/usr/bin/env python3
"""
视频处理工作流程编排器 - FastAPI 服务 (优化版)
"""
import logging
from pathlib import Path
from datetime import datetime
import os  # 新增导入，用于环境变量访问和路径操作

# 第三方库
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response
from dotenv import load_dotenv

# 本地模块
from settings import get_settings
from routers import upload, process, export, download, agent

# 自定义静态文件类，添加缓存头
class CustomStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200 and not path.endswith(".html"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

load_dotenv()
settings = get_settings()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('video_processing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 创建 FastAPI 应用
app = FastAPI(
    title="视频处理 API",
    description="视频转录、摘要和图文笔记生成服务",
    version="1.0.0"
)

# 启用 GZip 压缩（必须在 CORS 之前添加）
app.add_middleware(GZipMiddleware, minimum_size=500)

# 配置 CORS (生产环境建议指定具体源)
# 根据环境变量或设置动态配置允许的源，优先使用配置的 FRONTEND_URL，否则在本地模式下允许所有源
if settings.DEPLOYMENT_MODE == "local":
    allow_origins = ["*"]  # 本地开发允许所有源
else:
    # 生产环境：如果配置了 FRONTEND_URL，则使用它；否则默认为空列表（更安全）
    allow_origins = [settings.FRONTEND_URL] if settings.FRONTEND_URL else []
    # 你也可以添加其他可信的源，例如：
    # allow_origins = [settings.FRONTEND_URL, "https://another-trusted-domain.com"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,  # 如果前端需要携带认证信息（如cookies），请设置为True
    allow_methods=["*"],
    allow_headers=["*"],
)

# 动态生成 sitemap.xml
@app.get("/sitemap.xml", response_class=Response)
async def sitemap():
    urls = [
        "/", "/api/health", "/api/config", "/api/upload", "/api/process", "/api/export", "/api/download", "/api/agent"
    ]
    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    # 确保 settings 中有 public_api_base_url 属性，并在 settings.py 中设置默认值
    base_url = settings.public_api_base_url.rstrip("/") if hasattr(settings, 'public_api_base_url') and settings.public_api_base_url else "http://localhost:8000"
    for url in urls:
        xml.append(f'<url><loc>{base_url}{url}</loc></url>')
    xml.append('</urlset>')
    xml_str = '\n'.join(xml)
    return Response(content=xml_str, media_type="application/xml")

# 注册 API 路由（必须在静态文件挂载之前）
app.include_router(upload.router)
app.include_router(process.router)
app.include_router(export.router)
app.include_router(download.router)
app.include_router(agent.router)

# 基础配置查询（供前端读取运行时配置）
@app.get("/api/config")
async def api_config():
    return {"mode": settings.DEPLOYMENT_MODE, "api_base_url": settings.public_api_base_url}

# 挂载静态文件目录，添加缓存头
app.mount("/storage", CustomStaticFiles(directory="storage"), name="storage")

# 挂载前端静态文件（SPA，必须最后挂载），添加缓存头
frontend_dist = Path("zed-landing-vibe/dist")
if frontend_dist.exists():
    app.mount("/", CustomStaticFiles(directory=str(frontend_dist), html=True), name="frontend")
    logger.info("前端静态文件已挂载。")
else:
    logger.warning(f"前端静态文件目录不存在: {frontend_dist.absolute()}。前端页面将无法访问。")

@app.get("/")
async def root():
    return {"message": "视频处理 API 服务", "docs": "/docs"}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn

    # 确保存储目录存在
    storage_dir = Path("storage")
    storage_dir.mkdir(exist_ok=True)

    logger.info("🚀 启动视频处理 API 服务...")
    logger.info(f"📁 存储目录: {storage_dir.absolute()}")
    logger.info("🌐 API 文档: http://localhost:8000/docs")
    logger.info("🔍 健康检查: http://localhost:8000/api/health")
    logger.info("📤 上传接口: http://localhost:8000/api/upload")

    # 根据部署模式决定是否启用重载
    reload_enabled = settings.DEPLOYMENT_MODE == "local"

    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=reload_enabled,  # 仅在本地开发模式启用热重载
        log_level="info"
    )
