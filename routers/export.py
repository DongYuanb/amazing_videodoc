"""导出相关路由"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from services.task_manager import TaskManager
from utils.file_utils import find_notes_file, ensure_markdown_file, create_multimodal_generator
from markdown_pdf import MarkdownPdf, Section
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

    # 生成 Markdown（Web版本，用于前端预览）
    generator = create_multimodal_generator()
    generator.export_to_markdown(
        notes_json_path=str(notes_file),
        output_path=str(markdown_file),
        image_base_path=str(task_dir),
        for_web=True
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

    # 优先使用用户编辑的 notes.md，保留用户的裁剪和编辑
    if markdown_file.exists():
        # 读取用户编辑的内容
        with open(markdown_file, "r", encoding="utf-8") as f:
            markdown_content = f.read()

        # 将Web路径转换为PDF可用的相对路径
        import re
        # 转换绝对路径为相对路径
        markdown_content = re.sub(
            r'!\[([^\]]*)\]\(/storage/tasks/[^/]+/([^)]+)\)',
            r'![\1](\2)',
            markdown_content
        )
        temp_md_path = None  # 不需要临时文件
    else:
        # 如果用户没有编辑过，从JSON生成PDF专用内容
        notes_file = find_notes_file(task_dir)
        if not notes_file:
            raise HTTPException(status_code=404, detail="图文笔记文件不存在")

        generator = create_multimodal_generator()
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as temp_md:
            generator.export_to_markdown(
                notes_json_path=str(notes_file),
                output_path=temp_md.name,
                image_base_path=str(task_dir),
                for_web=False  # 使用相对路径，适合PDF生成
            )
            temp_md_path = temp_md.name

        # 读取生成的markdown内容
        with open(temp_md_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()

    # 创建 PDF 文件路径
    pdf_file = task_dir / f"video_notes_{task_id}.pdf"

    try:
        # 使用 markdown-pdf 生成 PDF
        generate_pdf_with_markdown_pdf(markdown_content, str(pdf_file), task_dir)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"PDF 生成失败: {str(e)}"
        )
    finally:
        # 清理临时文件（如果存在）
        if temp_md_path:
            import os
            try:
                os.unlink(temp_md_path)
            except:
                pass

    # 检查 PDF 文件是否成功创建
    if not pdf_file.exists():
        raise HTTPException(status_code=500, detail="PDF 文件创建失败")

    # 返回 PDF 文件
    return FileResponse(
        path=str(pdf_file),
        filename=f"video_notes_{task_id}.pdf",
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=video_notes_{task_id}.pdf"
        }
    )


def generate_pdf_with_markdown_pdf(markdown_content: str, pdf_path: str, task_dir) -> None:
    """使用 markdown-pdf 生成 PDF"""

    # 创建 PDF 对象，支持目录和优化
    pdf = MarkdownPdf(toc_level=3, optimize=True)

    # 设置文档属性
    pdf.meta["title"] = "📹 视频笔记"
    pdf.meta["author"] = "Video Processing API"
    pdf.meta["creator"] = "Amazing VideoDoc"
    pdf.meta["subject"] = "AI生成的视频图文笔记"

    # 自定义 CSS 样式，支持中文字体
    custom_css = """
    body {
        font-family: 'PingFang SC', 'Microsoft YaHei', 'SimSun', 'DejaVu Sans', sans-serif;
        line-height: 1.6;
        color: #333;
        font-size: 12px;
    }
    h1 {
        color: #2c3e50;
        font-size: 18px;
        margin-bottom: 20px;
        text-align: center;
    }
    h2 {
        color: #34495e;
        font-size: 16px;
        margin-bottom: 15px;
    }
    h3 {
        color: #7f8c8d;
        font-size: 14px;
        margin-bottom: 10px;
    }
    img {
        max-width: 100%;
        height: auto;
        margin: 10px 0;
        display: block;
    }
    table {
        border-collapse: collapse;
        width: 100%;
        margin: 10px 0;
    }
    th, td {
        border: 1px solid #ddd;
        padding: 8px;
        text-align: left;
    }
    th {
        background-color: #f2f2f2;
        font-weight: bold;
    }
    ul, ol {
        margin: 10px 0;
        padding-left: 20px;
    }
    li {
        margin: 5px 0;
    }
    p {
        margin: 8px 0;
    }
    """

    # 添加内容段落，设置图片根目录
    pdf.add_section(
        Section(markdown_content, root=str(task_dir)),
        user_css=custom_css
    )

    # 保存 PDF
    pdf.save(pdf_path)

