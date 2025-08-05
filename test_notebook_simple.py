#!/usr/bin/env python3
"""
简单的笔记生成测试脚本
"""

import os
import sys
from pathlib import Path

# 确保可以导入notebook模块
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def test_basic_import():
    """测试基本导入"""
    print("🔍 测试模块导入...")
    
    try:
        from notebook import NotebookGenerator, LayoutType
        print("✅ 导入成功")
        return True
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False

def test_basic_functionality():
    """测试基本功能"""
    print("🧪 测试基本功能...")
    
    try:
        from notebook import NotebookGenerator, LayoutType, create_notebook_generator
        
        # 创建生成器
        generator = create_notebook_generator(
            pdf_title="测试笔记",
            layout_type=LayoutType.BALANCED
        )
        
        print(f"✅ 生成器创建成功: {generator}")
        
        # 添加一些测试内容
        generator.add_text("这是测试文字", 10.0, speaker="测试")
        
        # 创建一个简单的测试图片
        from PIL import Image
        test_img = Image.new('RGB', (200, 150), color='red')
        test_img_path = "test_image.jpg"
        test_img.save(test_img_path)
        
        generator.add_image(test_img_path, 15.0, caption="测试图片")
        
        print(f"✅ 内容添加成功，总内容数: {len(generator.content_manager)}")
        
        # 获取统计信息
        stats = generator.get_statistics()
        print(f"📊 统计信息: {stats['total_contents']} 个内容")
        
        # 清理测试文件
        if os.path.exists(test_img_path):
            os.unlink(test_img_path)
        
        return True
        
    except Exception as e:
        print(f"❌ 功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pdf_generation():
    """测试PDF生成"""
    print("📄 测试PDF生成...")
    
    try:
        # 检查reportlab
        import reportlab
        print("✅ reportlab 可用")
    except ImportError:
        print("❌ reportlab 未安装，跳过PDF生成测试")
        return False
    
    try:
        from notebook import create_notebook_generator, LayoutType
        from PIL import Image
        
        # 创建生成器
        generator = create_notebook_generator(
            pdf_title="PDF测试笔记",
            layout_type=LayoutType.BALANCED
        )
        
        # 添加测试内容
        generator.add_text("这是PDF测试的第一段文字", 10.0, speaker="测试者")
        
        # 创建测试图片
        test_img = Image.new('RGB', (300, 200), color='blue')
        test_img_path = "test_pdf_image.jpg"
        test_img.save(test_img_path)
        
        generator.add_image(test_img_path, 15.0, caption="PDF测试图片")
        generator.add_text("这是PDF测试的第二段文字", 20.0, speaker="测试者")
        
        # 确保输出目录存在
        os.makedirs("output/notebooks", exist_ok=True)
        
        # 生成预览PDF
        preview_path = generator.generate_preview("output/notebooks/test_preview.pdf")
        print(f"✅ 预览PDF生成成功: {preview_path}")
        
        # 清理测试文件
        if os.path.exists(test_img_path):
            os.unlink(test_img_path)
        
        return True
        
    except Exception as e:
        print(f"❌ PDF生成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🚀 笔记生成系统简单测试")
    print("=" * 50)
    
    tests = [
        test_basic_import,
        test_basic_functionality,
        test_pdf_generation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()  # 空行分隔
        except Exception as e:
            print(f"❌ 测试异常: {e}")
    
    print("=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！")
        print("💡 现在可以运行完整的示例: python3 run_notebook_example.py")
    else:
        print("⚠️  部分测试失败，请检查环境配置")

if __name__ == "__main__":
    main()
