"""导出相关路由"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from services.task_manager import TaskManager
from utils.file_utils import find_notes_file, ensure_markdown_file, create_multimodal_generator
from utils.export_utils import embed_images_in_content, create_html_document
import re
import base64
from io import BytesIO
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image as PILImage
import platform
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

    # 不需要HTML处理，直接用markdown

    # 创建 PDF 文件路径
    pdf_file = task_dir / f"video_notes_{task_id}.pdf"
    
    try:
        # 使用 reportlab 生成简单的 PDF
        generate_simple_pdf(markdown_content, str(pdf_file), task_dir)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"PDF 生成失败: {str(e)}"
        )

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


def setup_chinese_fonts():
    """设置中文字体支持"""
    try:
        # 尝试注册系统中文字体
        system = platform.system()

        if system == "Darwin":  # macOS
            font_paths = [
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/Helvetica.ttc",
                "/Library/Fonts/Arial Unicode MS.ttf"
            ]
        elif system == "Windows":
            font_paths = [
                "C:/Windows/Fonts/msyh.ttc",  # 微软雅黑
                "C:/Windows/Fonts/simsun.ttc",  # 宋体
                "C:/Windows/Fonts/arial.ttf"
            ]
        else:  # Linux
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
            ]

        # 尝试注册第一个可用的字体
        for font_path in font_paths:
            try:
                if Path(font_path).exists():
                    pdfmetrics.registerFont(TTFont('ChineseFont', font_path))
                    return 'ChineseFont'
            except:
                continue

        # 如果都失败了，使用reportlab内置字体
        return 'Helvetica'

    except:
        return 'Helvetica'


def generate_simple_pdf(markdown_content: str, pdf_path: str, task_dir) -> None:
    """使用 reportlab 生成支持中文的 PDF"""
    # 设置中文字体
    chinese_font = setup_chinese_fonts()

    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # 创建支持中文的样式
    title_style = ParagraphStyle(
        'ChineseTitle',
        parent=styles['Heading1'],
        fontName=chinese_font,
        fontSize=18,
        spaceAfter=30,
        alignment=TA_CENTER
    )

    h1_style = ParagraphStyle(
        'ChineseH1',
        parent=styles['Heading1'],
        fontName=chinese_font,
        fontSize=16,
        spaceAfter=20
    )

    h2_style = ParagraphStyle(
        'ChineseH2',
        parent=styles['Heading2'],
        fontName=chinese_font,
        fontSize=14,
        spaceAfter=15
    )

    h3_style = ParagraphStyle(
        'ChineseH3',
        parent=styles['Heading3'],
        fontName=chinese_font,
        fontSize=12,
        spaceAfter=10
    )

    normal_style = ParagraphStyle(
        'ChineseNormal',
        parent=styles['Normal'],
        fontName=chinese_font,
        fontSize=10,
        spaceAfter=8
    )

    # 添加标题
    story.append(Paragraph("📹 视频笔记", title_style))
    story.append(Spacer(1, 20))

    # 处理markdown内容
    lines = markdown_content.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 8))
            continue

        # 转义HTML特殊字符，但保留emoji
        line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        if line.startswith('# '):
            # 一级标题
            story.append(Paragraph(line[2:], h1_style))
        elif line.startswith('## '):
            # 二级标题
            story.append(Paragraph(line[3:], h2_style))
        elif line.startswith('### '):
            # 三级标题
            story.append(Paragraph(line[4:], h3_style))
        elif line.startswith('!['):
            # 图片处理
            try:
                match = re.search(r'!\[([^\]]*)\]\(([^)]+)\)', line)
                if match:
                    alt_text = match.group(1)
                    img_path = match.group(2)

                    if not img_path.startswith('http'):
                        # 本地图片
                        if img_path.startswith('/storage/'):
                            img_path = img_path[9:]
                        full_img_path = task_dir.parent.parent / img_path

                        if full_img_path.exists():
                            # 获取图片尺寸并调整
                            with PILImage.open(full_img_path) as pil_img:
                                width, height = pil_img.size
                                # 限制最大宽度为4英寸
                                max_width = 4 * inch
                                if width > max_width:
                                    ratio = max_width / width
                                    width = max_width
                                    height = height * ratio
                                else:
                                    width = width * 0.75  # 转换为点
                                    height = height * 0.75

                            img = RLImage(str(full_img_path), width=width, height=height)
                            story.append(img)
                            if alt_text:
                                story.append(Paragraph(f"图片说明: {alt_text}", normal_style))
                            story.append(Spacer(1, 12))
                        else:
                            story.append(Paragraph(f"[图片未找到: {alt_text}]", normal_style))
            except Exception:
                story.append(Paragraph(f"[图片处理失败: {line}]", normal_style))
        elif line.startswith('- ') or line.startswith('* '):
            # 列表项
            story.append(Paragraph(f"• {line[2:]}", normal_style))
        elif line.startswith('**') and line.endswith('**'):
            # 粗体文本
            content = line[2:-2]
            story.append(Paragraph(f"<b>{content}</b>", normal_style))
        else:
            # 普通文本
            if line:
                story.append(Paragraph(line, normal_style))

    doc.build(story)