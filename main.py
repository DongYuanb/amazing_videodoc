#!/usr/bin/env python3
"""
视频处理工作流程编排器 - FastAPI 服务
"""
import logging
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

# 自定义静态文件类，添加缓存头
class CustomStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200 and not path.endswith(".html"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response
from dotenv import load_dotenv
from settings import get_settings

# 导入路由
from routers import upload, process, export, download, agent

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

# 配置 CORS (production respects FRONTEND_URL if provided)
allow_origins = ["*"] if settings.DEPLOYMENT_MODE == "local" or not settings.FRONTEND_URL else [settings.FRONTEND_URL]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 动态生成 sitemap.xml
from fastapi.responses import Response
@app.get("/sitemap.xml", response_class=Response)
async def sitemap():
    # 可根据实际路由动态生成
    urls = [
        "/", "/api/health", "/api/config", "/api/upload", "/api/process", "/api/export", "/api/download", "/api/agent"
    ]
    xml = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    for url in urls:
        xml.append(f'<url><loc>{{base_url}}{url}</loc></url>')
    xml.append('</urlset>')
    base_url = settings.public_api_base_url.rstrip("/") if hasattr(settings, "public_api_base_url") else "http://localhost:8000"
    xml_str = '\n'.join([line.replace("{base_url}", base_url) for line in xml])
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

    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=True,
        log_level="info"
    )
