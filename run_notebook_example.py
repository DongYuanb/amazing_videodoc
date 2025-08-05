#!/usr/bin/env python3
"""
图文混排笔记生成系统启动脚本

在项目根目录运行此脚本来演示笔记生成功能
"""

import os
import sys
from pathlib import Path

# 确保可以导入notebook模块
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 现在可以正常导入
from notebook.notebook_generator import NotebookGenerator, NotebookConfig, create_notebook_generator
from notebook.layout_engine import LayoutType
from notebook.notebook_content import TimeRange


def example_basic_usage():
    """示例1: 基本使用方法"""
    print("🎯 示例1: 基本使用方法")
    print("=" * 50)
    
    # 创建笔记生成器
    generator = create_notebook_generator(
        pdf_title="AI讲座笔记",
        pdf_author="自动生成系统",
        layout_type=LayoutType.BALANCED,
        time_window=30.0
    )
    
    # 添加示例内容
    print("📝 添加示例内容...")
    
    # 检查是否有实际的图片文件
    frame_dir = "output/unique_frames"
    if os.path.exists(frame_dir):
        frame_files = [f for f in os.listdir(frame_dir) if f.endswith('.jpg')]
        if frame_files:
            # 使用实际的图片文件
            for i, frame_file in enumerate(frame_files[:4]):  # 最多使用4张图片
                frame_path = os.path.join(frame_dir, frame_file)
                timestamp = 10.0 + i * 30.0  # 每30秒一张图片
                generator.add_image(
                    frame_path,
                    timestamp=timestamp,
                    caption=f"视频帧 {i+1}",
                    quality_score=0.9 - i * 0.05,
                    source="video_frame"
                )
                
                # 添加对应的文字内容
                texts = [
                    "欢迎大家参加今天的人工智能发展趋势讲座。",
                    "今天我们将从历史发展、技术突破等角度探讨AI。",
                    "人工智能的发展经历了多个重要的历史阶段。",
                    "让我们来看看AI技术的具体应用场景。"
                ]
                if i < len(texts):
                    generator.add_text(
                        texts[i],
                        timestamp=timestamp + 2.0,
                        confidence=0.92 - i * 0.02,
                        speaker="讲师",
                        source="speech_to_text"
                    )
        else:
            print("⚠️  未找到视频帧文件，使用模拟数据")
            add_mock_content(generator)
    else:
        print("⚠️  未找到视频帧目录，使用模拟数据")
        add_mock_content(generator)
    
    # 显示统计信息
    stats = generator.get_statistics()
    print(f"📊 内容统计:")
    print(f"  • 总内容数: {stats['total_contents']}")
    print(f"  • 图片数: {stats['image_count']}")
    print(f"  • 文字数: {stats['text_count']}")
    if stats['time_range']:
        print(f"  • 时间范围: {stats['time_range']['start_time']:.1f}s - {stats['time_range']['end_time']:.1f}s")
    
    # 生成预览
    print("🔍 生成预览PDF...")
    try:
        preview_path = generator.generate_preview()
        print(f"✅ 预览生成成功: {preview_path}")
    except Exception as e:
        print(f"❌ 预览生成失败: {e}")
        return
    
    # 生成完整笔记
    print("📚 生成完整笔记...")
    try:
        notebook_path = generator.generate_notebook()
        print(f"✅ 笔记生成成功: {notebook_path}")
    except Exception as e:
        print(f"❌ 笔记生成失败: {e}")


def add_mock_content(generator):
    """添加模拟内容"""
    # 创建模拟图片（1x1像素的占位符）
    from PIL import Image
    import tempfile
    
    mock_images = []
    for i in range(4):
        # 创建简单的彩色图片
        img = Image.new('RGB', (400, 300), color=(50 + i * 50, 100, 150))
        temp_path = f"temp_mock_image_{i}.jpg"
        img.save(temp_path, "JPEG")
        mock_images.append(temp_path)
    
    # 添加模拟内容
    contents = [
        ("欢迎大家参加今天的人工智能发展趋势讲座。", "开场PPT"),
        ("今天我们将从历史发展、技术突破等角度探讨AI。", "议程介绍"),
        ("人工智能的发展经历了多个重要的历史阶段。", "发展历程"),
        ("让我们来看看AI技术的具体应用场景。", "应用场景")
    ]
    
    for i, (text, caption) in enumerate(contents):
        timestamp = 10.0 + i * 30.0
        
        generator.add_image(
            mock_images[i],
            timestamp=timestamp,
            caption=caption,
            quality_score=0.9 - i * 0.05,
            source="mock_data"
        )
        
        generator.add_text(
            text,
            timestamp=timestamp + 2.0,
            confidence=0.92 - i * 0.02,
            speaker="讲师",
            source="mock_data"
        )
    
    return mock_images


def example_different_layouts():
    """示例2: 不同布局模式对比"""
    print("\n🎯 示例2: 不同布局模式对比")
    print("=" * 50)
    
    # 准备示例内容
    def add_sample_content(generator):
        mock_images = add_mock_content(generator)
        return mock_images
    
    layouts = [
        (LayoutType.IMAGE_DOMINANT, "图片主导"),
        (LayoutType.TEXT_DOMINANT, "文字主导"),
        (LayoutType.BALANCED, "平衡布局")
    ]
    
    all_mock_images = []
    
    for layout_type, layout_name in layouts:
        print(f"📐 测试 {layout_name} 布局...")
        
        generator = create_notebook_generator(
            pdf_title=f"测试笔记 - {layout_name}",
            layout_type=layout_type,
            time_window=25.0
        )
        
        mock_images = add_sample_content(generator)
        all_mock_images.extend(mock_images)
        
        try:
            output_path = f"output/notebooks/test_{layout_type.value}.pdf"
            generator.generate_notebook(output_path)
            print(f"  ✅ {layout_name} 布局生成成功")
        except Exception as e:
            print(f"  ❌ {layout_name} 布局生成失败: {e}")
    
    # 清理临时文件
    cleanup_mock_images(all_mock_images)


def cleanup_mock_images(image_paths):
    """清理临时图片文件"""
    for path in image_paths:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except Exception as e:
            print(f"Warning: Failed to cleanup {path}: {e}")


def check_dependencies():
    """检查依赖"""
    print("🔍 检查依赖...")
    
    required_modules = [
        ('reportlab', 'PDF生成'),
        ('PIL', '图片处理'),
    ]
    
    missing = []
    for module, desc in required_modules:
        try:
            if module == 'PIL':
                import PIL
            else:
                __import__(module)
            print(f"  ✅ {module} ({desc})")
        except ImportError:
            print(f"  ❌ {module} ({desc}) - 未安装")
            missing.append(module)
    
    if missing:
        print(f"\n⚠️  缺少依赖: {', '.join(missing)}")
        print("请运行: pip install reportlab pillow")
        return False
    
    print("✅ 所有依赖已安装")
    return True


def main():
    """主函数"""
    print("📚 图文混排笔记生成系统示例")
    print("=" * 60)
    
    # 检查依赖
    if not check_dependencies():
        return
    
    # 确保输出目录存在
    os.makedirs("output/notebooks", exist_ok=True)
    
    try:
        # 运行示例
        example_basic_usage()
        example_different_layouts()
        
        print("\n" + "=" * 60)
        print("🎉 示例运行完成！")
        print("📁 生成的文件保存在: output/notebooks/")
        print("\n💡 提示:")
        print("- 如果有实际的视频帧文件，请放在 output/unique_frames/ 目录下")
        print("- 可以修改 notebook_config_example.json 来自定义配置")
        print("- 查看 NOTEBOOK_GUIDE.md 了解详细使用方法")
        
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
