#!/usr/bin/env python3
"""
图文混排笔记生成示例

演示如何使用NotebookGenerator创建图文混排的PDF笔记，
包括从视频帧去重系统集成、配置管理、多种布局模式等功能。
"""

import os
import sys
from pathlib import Path
from datetime import datetime

import sys
import os
# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
    
    # 模拟从视频帧去重系统获得的图片
    generator.add_image(
        "./output/unique_frames/unique_frame_000001.jpg", 
        timestamp=10.0,
        caption="开场PPT - 欢迎页面",
        quality_score=0.95,
        source="video_frame"
    )
    
    # 模拟从语音转文字系统获得的文字
    generator.add_text(
        "欢迎大家参加今天的人工智能发展趋势讲座。今天我们将从历史发展、技术突破、应用场景等多个角度来探讨AI的现状和未来。",
        timestamp=12.0,
        confidence=0.92,
        speaker="讲师",
        source="speech_to_text"
    )
    
    generator.add_image(
        "./output/unique_frames/unique_frame_000002.jpg",
        timestamp=45.0,
        caption="AI发展历程时间线",
        quality_score=0.88,
        source="video_frame"
    )
    
    generator.add_text(
        "人工智能的发展可以分为三个主要阶段：符号主义时期、连接主义时期，以及当前的深度学习时期。每个时期都有其独特的技术特点和应用场景。",
        timestamp=47.0,
        confidence=0.89,
        speaker="讲师",
        source="speech_to_text"
    )
    
    # 显示统计信息
    stats = generator.get_statistics()
    print(f"📊 内容统计:")
    print(f"  • 总内容数: {stats['total_contents']}")
    print(f"  • 图片数: {stats['image_count']}")
    print(f"  • 文字数: {stats['text_count']}")
    print(f"  • 时间范围: {stats['time_range']}")
    
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


def example_different_layouts():
    """示例2: 不同布局模式对比"""
    print("\n🎯 示例2: 不同布局模式对比")
    print("=" * 50)
    
    # 准备示例内容
    def add_sample_content(generator):
        generator.add_image("slide1.jpg", 10.0, caption="PPT第一页")
        generator.add_text("这是第一段讲解内容", 12.0, speaker="讲师")
        generator.add_image("slide2.jpg", 30.0, caption="PPT第二页")
        generator.add_text("这是第二段讲解内容", 32.0, speaker="讲师")
    
    layouts = [
        (LayoutType.IMAGE_DOMINANT, "图片主导"),
        (LayoutType.TEXT_DOMINANT, "文字主导"),
        (LayoutType.BALANCED, "平衡布局")
    ]
    
    for layout_type, layout_name in layouts:
        print(f"📐 测试 {layout_name} 布局...")
        
        generator = create_notebook_generator(
            pdf_title=f"测试笔记 - {layout_name}",
            layout_type=layout_type,
            time_window=25.0
        )
        
        add_sample_content(generator)
        
        try:
            output_path = f"output/notebooks/test_{layout_type.value}.pdf"
            generator.generate_notebook(output_path)
            print(f"  ✅ {layout_name} 布局生成成功")
        except Exception as e:
            print(f"  ❌ {layout_name} 布局生成失败: {e}")


def example_config_management():
    """示例3: 配置管理"""
    print("\n🎯 示例3: 配置管理")
    print("=" * 50)
    
    # 从配置文件创建生成器
    config_path = "notebook_config_example.json"
    
    if os.path.exists(config_path):
        print(f"📄 从配置文件加载: {config_path}")
        generator = create_notebook_generator(config_path=config_path)
    else:
        print("⚠️  配置文件不存在，使用默认配置")
        generator = create_notebook_generator()
    
    # 显示当前配置
    print("⚙️  当前配置:")
    config_dict = generator.config.to_dict()
    for key, value in config_dict.items():
        print(f"  • {key}: {value}")
    
    # 动态更新配置
    print("\n🔧 更新配置...")
    generator.update_config(
        pdf_title="动态更新的笔记标题",
        time_window=20.0,
        show_timestamps=False
    )
    
    # 保存配置
    new_config_path = "output/my_notebook_config.json"
    generator.save_config(new_config_path)
    print(f"💾 配置已保存到: {new_config_path}")


def example_time_filtering():
    """示例4: 时间范围过滤"""
    print("\n🎯 示例4: 时间范围过滤")
    print("=" * 50)
    
    generator = create_notebook_generator(
        pdf_title="时间过滤示例",
        time_window=15.0
    )
    
    # 添加不同时间段的内容
    time_segments = [
        (10.0, "开场介绍"),
        (30.0, "第一部分内容"),
        (60.0, "第二部分内容"),
        (90.0, "第三部分内容"),
        (120.0, "总结部分")
    ]
    
    for timestamp, content in time_segments:
        generator.add_text(content, timestamp, speaker="讲师")
        generator.add_image(f"slide_{int(timestamp)}.jpg", timestamp + 2, 
                          caption=f"时间点 {timestamp}s 的PPT")
    
    print(f"📊 总内容数: {len(generator.content_manager)}")
    
    # 设置时间过滤：只要30-90秒的内容
    print("⏰ 设置时间过滤: 30-90秒")
    generator.set_time_filter(30.0, 90.0)
    
    filtered_contents = generator.get_filtered_contents()
    print(f"📊 过滤后内容数: {len(filtered_contents)}")
    
    # 生成过滤后的笔记
    try:
        output_path = "output/notebooks/filtered_notebook.pdf"
        generator.generate_notebook(output_path)
        print(f"✅ 过滤笔记生成成功: {output_path}")
    except Exception as e:
        print(f"❌ 过滤笔记生成失败: {e}")


def example_integration_with_video_system():
    """示例5: 与视频处理系统集成"""
    print("\n🎯 示例5: 与视频处理系统集成")
    print("=" * 50)
    
    # 模拟从视频帧去重系统获取结果
    def simulate_video_dedup_result():
        """模拟视频去重系统的输出"""
        return {
            'video_path': '/path/to/lecture.mp4',
            'time_range': (10.0, 300.0),
            'unique_frames': [
                {'path': 'frame_001.jpg', 'timestamp': 15.0, 'quality': 0.95},
                {'path': 'frame_002.jpg', 'timestamp': 45.0, 'quality': 0.88},
                {'path': 'frame_003.jpg', 'timestamp': 75.0, 'quality': 0.92},
                {'path': 'frame_004.jpg', 'timestamp': 105.0, 'quality': 0.87},
            ]
        }
    
    # 模拟从语音转文字系统获取结果
    def simulate_speech_to_text_result():
        """模拟语音转文字系统的输出"""
        return [
            {'text': '欢迎大家参加今天的讲座', 'timestamp': 12.0, 'confidence': 0.95},
            {'text': '首先我们来看第一个主题', 'timestamp': 42.0, 'confidence': 0.89},
            {'text': '这个图表显示了发展趋势', 'timestamp': 72.0, 'confidence': 0.91},
            {'text': '接下来我们讨论应用场景', 'timestamp': 102.0, 'confidence': 0.88},
        ]
    
    # 创建笔记生成器
    generator = create_notebook_generator(
        pdf_title="集成示例 - 讲座笔记",
        layout_type=LayoutType.BALANCED,
        time_window=30.0
    )
    
    # 集成视频帧数据
    print("🖼️  集成视频帧数据...")
    video_result = simulate_video_dedup_result()
    for frame in video_result['unique_frames']:
        generator.add_image(
            frame['path'],
            frame['timestamp'],
            quality_score=frame['quality'],
            source='video_deduplicator'
        )
    
    # 集成语音转文字数据
    print("🎤 集成语音转文字数据...")
    speech_result = simulate_speech_to_text_result()
    for speech in speech_result:
        generator.add_text(
            speech['text'],
            speech['timestamp'],
            confidence=speech['confidence'],
            source='speech_to_text'
        )
    
    # 设置时间范围（与视频处理范围一致）
    start_time, end_time = video_result['time_range']
    generator.set_time_filter(start_time, end_time)
    
    print(f"📊 集成完成:")
    stats = generator.get_statistics()
    print(f"  • 图片: {stats['image_count']}")
    print(f"  • 文字: {stats['text_count']}")
    print(f"  • 时间范围: {stats['time_range']}")
    
    # 生成集成笔记
    try:
        output_path = "output/notebooks/integrated_notebook.pdf"
        generator.generate_notebook(output_path)
        print(f"✅ 集成笔记生成成功: {output_path}")
    except Exception as e:
        print(f"❌ 集成笔记生成失败: {e}")


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
        example_config_management()
        example_time_filtering()
        example_integration_with_video_system()
        
        print("\n" + "=" * 60)
        print("🎉 所有示例运行完成！")
        print("📁 生成的文件保存在: output/notebooks/")
        
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
