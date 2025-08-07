#!/usr/bin/env python3
"""
带图片裁剪功能的视频帧去重示例

演示如何在视频帧去重过程中加入图片裁剪功能，
特别适用于讲课、会议等场景，可以只保留PPT内容。
"""

import os
from video_frame_deduplicator import VideoFrameDeduplicator
from image_preprocessor import (
    create_preprocessor, 
    CropRegion, 
    TemplateCropper,
    ManualCropper,
    ConfigurableCropper,
    InteractiveCropper
)


def example_template_cropping():
    """示例1: 使用预设模板裁剪"""
    print("🎯 示例1: 使用预设模板裁剪")
    print("=" * 50)
    
    # 显示可用模板
    print("可用的预设模板:")
    for name, desc in TemplateCropper.list_templates().items():
        print(f"  • {name}: {desc}")
    
    # 创建模板裁剪器
    preprocessor = create_preprocessor(
        'template', 
        template_name='lecture_ppt_only'  # 讲课场景，只保留PPT
    )
    
    # 创建去重处理器
    deduplicator = VideoFrameDeduplicator(
        jina_api_key=os.getenv("JINA_API_KEY"),
        similarity_threshold=0.85,
        image_preprocessor=preprocessor
    )
    
    # 处理视频
    video_path = "/Users/musk/Documents/code/amazing_videodoc/upload/demo_video.mp4"
    if os.path.exists(video_path):
        result = deduplicator.process_video_frames(
            video_path=video_path,
            start_time=10.0,
            end_time=30.0,
            output_dir="output/cropped_frames_template",
            fps=0.5
        )
        print(f"✅ 模板裁剪完成，保存到: {result['output_dir']}")
    else:
        print(f"❌ 视频文件不存在: {video_path}")


def example_manual_cropping():
    """示例2: 手动指定裁剪区域"""
    print("\n🎯 示例2: 手动指定裁剪区域")
    print("=" * 50)
    
    # 定义裁剪区域 (去除边缘10%，保留中心80%区域)
    crop_region = CropRegion(
        left=0.1,    # 左边界：10%
        top=0.1,     # 上边界：10%
        right=0.9,   # 右边界：90%
        bottom=0.9,  # 下边界：90%
        is_relative=True  # 使用相对坐标
    )
    
    print(f"裁剪区域: {crop_region}")
    
    # 创建手动裁剪器
    preprocessor = ManualCropper(crop_region, quality=95)
    
    # 创建去重处理器
    deduplicator = VideoFrameDeduplicator(
        jina_api_key=os.getenv("JINA_API_KEY"),
        similarity_threshold=0.85,
        image_preprocessor=preprocessor
    )
    
    print("手动裁剪配置完成")


def example_config_cropping():
    """示例3: 使用配置文件裁剪"""
    print("\n🎯 示例3: 使用配置文件裁剪")
    print("=" * 50)
    
    config_path = "crop_config_example.json"
    
    if os.path.exists(config_path):
        # 创建配置裁剪器
        preprocessor = ConfigurableCropper(config_path, quality=95)
        
        print(f"从配置文件加载裁剪设置: {config_path}")
        print(f"裁剪区域: {preprocessor.crop_region}")
        
        # 创建去重处理器
        deduplicator = VideoFrameDeduplicator(
            jina_api_key=os.getenv("JINA_API_KEY"),
            similarity_threshold=0.85,
            image_preprocessor=preprocessor
        )
        
        print("配置文件裁剪设置完成")
    else:
        print(f"❌ 配置文件不存在: {config_path}")


def example_interactive_cropping():
    """示例4: 交互式裁剪"""
    print("\n🎯 示例4: 交互式裁剪")
    print("=" * 50)
    
    # 创建交互式裁剪器
    preprocessor = InteractiveCropper(quality=95)
    
    # 使用样本图片设置裁剪区域
    video_path = "/Users/musk/Documents/code/amazing_videodoc/upload/demo_video.mp4"
    
    if os.path.exists(video_path):
        print("首先需要设置裁剪区域...")
        
        # 先抽取一帧作为样本
        temp_deduplicator = VideoFrameDeduplicator(
            jina_api_key=os.getenv("JINA_API_KEY")
        )
        
        # 抽取一帧作为样本
        sample_frames = temp_deduplicator.extract_frames(
            video_path, 15.0, 16.0, 1.0, "temp_sample"
        )
        
        if sample_frames:
            # 设置裁剪区域
            crop_region = preprocessor.setup_crop_region(sample_frames[0])
            
            # 创建完整的去重处理器
            deduplicator = VideoFrameDeduplicator(
                jina_api_key=os.getenv("JINA_API_KEY"),
                similarity_threshold=0.85,
                image_preprocessor=preprocessor
            )
            
            print("交互式裁剪设置完成")
            
            # 清理样本文件
            import shutil
            if os.path.exists("temp_sample"):
                shutil.rmtree("temp_sample")
        else:
            print("❌ 无法抽取样本帧")
    else:
        print(f"❌ 视频文件不存在: {video_path}")


def show_cropping_tips():
    """显示裁剪使用技巧"""
    print("\n💡 图片裁剪使用技巧")
    print("=" * 50)
    
    tips = [
        "1. 坐标系统说明:",
        "   • 相对坐标: 0.0-1.0，推荐使用",
        "   • 绝对坐标: 像素值，适合精确控制",
        "",
        "2. 常见场景配置:",
        "   • 讲师在右侧: left=0.0, right=0.7",
        "   • 讲师在左侧: left=0.3, right=1.0", 
        "   • 去除边缘: left=0.1, top=0.1, right=0.9, bottom=0.9",
        "",
        "3. 预设模板选择:",
        "   • lecture_ppt_only: 适合大多数讲课场景",
        "   • meeting_screen: 适合会议屏幕共享",
        "   • ppt_16_9_center: 适合居中的PPT显示",
        "",
        "4. 质量设置:",
        "   • quality=95: 高质量，文件较大",
        "   • quality=85: 平衡质量和大小",
        "   • quality=75: 较小文件，质量可接受",
        "",
        "5. 交互式裁剪使用:",
        "   • 先生成预览图片查看网格",
        "   • 根据网格确定裁剪坐标",
        "   • 输入格式: left top right bottom"
    ]
    
    for tip in tips:
        print(tip)


def main():
    """主函数"""
    print("🖼️  视频帧去重 + 图片裁剪功能演示")
    print("=" * 60)
    
    # 检查视频文件
    video_path = "/Users/musk/Documents/code/amazing_videodoc/upload/demo_video.mp4"
    if not os.path.exists(video_path):
        print(f"❌ 视频文件不存在: {video_path}")
        print("请确保视频文件存在后再运行示例")
        return
    
    # 运行示例
    try:
        example_template_cropping()
        example_manual_cropping()
        example_config_cropping()
        example_interactive_cropping()  # 需要用户交互，注释掉
        
        show_cropping_tips()
        
    except Exception as e:
        print(f"❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
