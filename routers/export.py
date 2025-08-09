"""导出相关路由"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from services.task_manager import TaskManager
from utils.file_utils import find_notes_file, ensure_markdown_file, create_multimodal_generator
from utils.export_utils import embed_images_in_content, create_html_document

router = APIRouter(prefix="/api", tags=["export"])

# 全局任务管理器实例
task_manager = TaskManager()


@router.get("/export/{task_id}/markdown")
async def export_markdown(task_id: str, force_regen: bool = False):
    """导出 Markdown 格式笔记（优先使用用户编辑版本）"""
    task_manager.validate_task_completed(task_id)
    task_dir = task_manager.get_task_dir(task_id)
    markdown_file = task_dir / "notes.md"

    # 如果用户编辑的 notes.md 存在且不强制重新生成，直接返回
    if markdown_file.exists() and not force_regen:
        return FileResponse(
            path=str(markdown_file),
            filename=f"video_notes_{task_id}.md",
            media_type="text/markdown"
        )

    # 否则从 JSON 重新生成
    notes_file = find_notes_file(task_dir)
    if not notes_file:
        raise HTTPException(status_code=404, detail="图文笔记文件不存在")

    # 生成 Markdown
    generator = create_multimodal_generator()
    generator.export_to_markdown(
        notes_json_path=str(notes_file),
        output_path=str(markdown_file),
        image_base_path=str(task_dir)
    )

    return FileResponse(
        path=str(markdown_file),
        filename=f"video_notes_{task_id}.md",
        media_type="text/markdown"
    )


@router.get("/export/{task_id}/json")
async def export_json(task_id: str):
    """导出原始 JSON 格式笔记"""
    task_manager.validate_task_completed(task_id)
    task_dir = task_manager.get_task_dir(task_id)
    
    notes_file = find_notes_file(task_dir)
    if not notes_file:
        raise HTTPException(status_code=404, detail="图文笔记文件不存在")

    return FileResponse(
        path=str(notes_file),
        filename=f"video_notes_{task_id}.json",
        media_type="application/json"
    )


@router.get("/notes/{task_id}")
async def get_notes(task_id: str):
    """获取笔记内容（优先返回用户编辑版本）"""
    task_manager.validate_task_completed(task_id)
    task_dir = task_manager.get_task_dir(task_id)
    markdown_file = task_dir / "notes.md"

    # 如果用户编辑的 notes.md 存在，直接返回
    if markdown_file.exists():
        return FileResponse(
            path=str(markdown_file),
            media_type="text/markdown"
        )

    # 否则从 JSON 生成 markdown
    notes_file = find_notes_file(task_dir)
    if not notes_file:
        raise HTTPException(status_code=404, detail="图文笔记文件不存在")

    # 确保 markdown 文件存在
    markdown_file = ensure_markdown_file(task_dir, notes_file)

    return FileResponse(
        path=str(markdown_file),
        media_type="text/markdown"
    )


@router.put("/notes/{task_id}")
async def save_notes(task_id: str, content: dict):
    """保存用户编辑的笔记内容"""
    task_manager.validate_task_completed(task_id)

    if "content" not in content:
        raise HTTPException(status_code=400, detail="缺少 content 字段")

    task_dir = task_manager.get_task_dir(task_id)
    markdown_file = task_dir / "notes.md"

    # 保存用户编辑的内容
    try:
        with open(markdown_file, "w", encoding="utf-8") as f:
            f.write(content["content"])

        return {"message": "笔记保存成功", "task_id": task_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存失败: {str(e)}")


@router.get("/export/{task_id}/pdf")
async def export_pdf(task_id: str):
    """导出 PDF 格式笔记（包含嵌入图片）"""
    task_manager.validate_task_completed(task_id)
    task_dir = task_manager.get_task_dir(task_id)
    markdown_file = task_dir / "notes.md"

    # 确保 markdown 文件存在
    if not markdown_file.exists():
        notes_file = find_notes_file(task_dir)
        if not notes_file:
            raise HTTPException(status_code=404, detail="图文笔记文件不存在")
        
        markdown_file = ensure_markdown_file(task_dir, notes_file)

    # 读取 markdown 内容
    with open(markdown_file, "r", encoding="utf-8") as f:
        markdown_content = f.read()

    # 嵌入图片并创建HTML
    content_with_images = embed_images_in_content(markdown_content, task_dir)
    full_html = create_html_document(content_with_images, task_id)

    # 保存 HTML 文件
    html_file = task_dir / "notes.html"
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(full_html)

    # 返回 HTML 文件（浏览器可以打印为 PDF）
    return FileResponse(
        path=str(html_file),
        filename=f"video_notes_{task_id}.html",
        media_type="text/html"
    )
