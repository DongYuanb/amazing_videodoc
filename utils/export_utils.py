"""导出功能工具函数"""
import base64
import re
from pathlib import Path


def embed_images_in_content(content: str, task_dir: Path) -> str:
    """将markdown内容中的图片转换为base64嵌入"""
    def replace_image(match):
        alt_text = match.group(1)
        image_path = match.group(2)

        # 处理不同的路径格式
        if not image_path.startswith('/') and not image_path.startswith('http'):
            full_path = task_dir / image_path
        elif image_path.startswith('/storage/'):
            relative_path = image_path[9:]  # 移除 '/storage/'
            full_path = Path("storage") / relative_path
        else:
            return match.group(0)  # 保持原样

        try:
            if full_path.exists():
                with open(full_path, "rb") as img_file:
                    img_data = base64.b64encode(img_file.read()).decode()
                    ext = full_path.suffix.lower()
                    mime_type = "image/jpeg" if ext in ['.jpg', '.jpeg'] else f"image/{ext[1:]}"
                    return f'<img src="data:{mime_type};base64,{img_data}" alt="{alt_text}" style="max-width: 100%; height: auto;">'
            else:
                return f'<p><em>图片未找到: {image_path}</em></p>'
        except Exception:
            return f'<p><em>图片加载失败: {image_path}</em></p>'

    pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    return re.sub(pattern, replace_image, content)



