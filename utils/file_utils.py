"""文件操作工具函数"""
import os
from pathlib import Path
from typing import Optional
from multimodal_note_generator import MultimodalNoteGenerator

def find_notes_file(task_dir: Path) -> Optional[Path]:
    """查找图文笔记文件，统一处理重复逻辑"""
    # 优先查找嵌套目录中的文件
    notes_file = task_dir / "multimodal_notes" / "multimodal_notes.json"
    if notes_file.exists():
        return notes_file
    
    # 备选：根目录中的文件
    notes_file = task_dir / "multimodal_notes.json"
    if notes_file.exists():
        return notes_file
    
    return None


def ensure_markdown_file(task_dir: Path, notes_file: Path) -> Path:
    """确保markdown文件存在，如果不存在则生成"""


    markdown_file = task_dir / "notes.md"

    if not markdown_file.exists():
        generator = MultimodalNoteGenerator(
            cohere_api_key=os.getenv("COHERE_API_KEY", "dummy")
        )
        generator.export_to_markdown(
            notes_json_path=str(notes_file),
            output_path=str(markdown_file),
            image_base_path=str(task_dir)
        )

    return markdown_file


def create_multimodal_generator():
    """创建图文笔记生成器的统一方法"""
    from multimodal_note_generator import MultimodalNoteGenerator
    return MultimodalNoteGenerator(
        cohere_api_key=os.getenv("COHERE_API_KEY", "dummy")
    )
