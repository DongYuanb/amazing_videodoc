#!/usr/bin/env python3
"""
测试在线视频下载API功能
"""
import requests
import time
import json
from pathlib import Path

API_BASE = "http://localhost:8000"

def test_supported_platforms():
    """测试获取支持的平台"""
    print("🔍 测试获取支持的平台...")
    try:
        response = requests.get(f"{API_BASE}/api/supported-platforms")
        if response.status_code == 200:
            platforms = response.json()
            print("✅ 支持的平台:")
            for platform in platforms["platforms"]:
                status = "✅" if platform["supported"] else "⏳"
                print(f"  {status} {platform['name']} ({platform['value']})")
            return True
        else:
            print(f"❌ 获取平台失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

def test_preview_video(url):
    """测试预览视频信息"""
    print(f"📋 测试预览视频信息: {url}")
    try:
        response = requests.post(f"{API_BASE}/api/preview-video", json={"url": url})
        if response.status_code == 200:
            info = response.json()
            print("✅ 视频信息:")
            print(f"  标题: {info.get('title', 'Unknown')}")
            print(f"  时长: {info.get('duration', 0)}秒")
            print(f"  平台: {info.get('platform', 'Unknown')}")
            print(f"  上传者: {info.get('uploader', 'Unknown')}")
            return info
        else:
            print(f"❌ 预览失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 预览异常: {e}")
        return None

def test_download_video(url, quality="medium"):
    """测试下载视频"""
    print(f"📥 测试下载视频: {url}")
    try:
        response = requests.post(f"{API_BASE}/api/download-url", json={
            "url": url,
            "quality": quality
        })
        if response.status_code == 200:
            result = response.json()
            task_id = result["task_id"]
            print(f"✅ 下载已开始，任务ID: {task_id}")
            print(f"  平台: {result.get('platform', 'Unknown')}")
            print(f"  标题: {result.get('title', 'Unknown')}")
            return task_id
        else:
            print(f"❌ 下载失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 下载异常: {e}")
        return None

def test_monitor_progress(task_id, max_wait=300):
    """测试监控下载进度"""
    print(f"📊 监控任务进度: {task_id}")
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{API_BASE}/api/download-status/{task_id}")
            if response.status_code == 200:
                status = response.json()
                progress = status.get("progress", 0)
                current_status = status.get("status", "unknown")
                
                print(f"📈 状态: {current_status} | 总进度: {progress:.1%}")
                
                if "download_progress" in status:
                    print(f"   下载进度: {status['download_progress']:.1%}")
                if "processing_progress" in status:
                    print(f"   处理进度: {status['processing_progress']:.1%}")
                
                if current_status == "completed":
                    print("✅ 任务完成！")
                    return True
                elif current_status == "failed":
                    error = status.get("error_message", "Unknown error")
                    print(f"❌ 任务失败: {error}")
                    return False
                
                time.sleep(5)
            else:
                print(f"❌ 状态查询失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 状态查询异常: {e}")
            return False
    
    print("⏰ 等待超时")
    return False

def test_get_results(task_id):
    """测试获取处理结果"""
    print(f"📋 获取处理结果: {task_id}")
    try:
        response = requests.get(f"{API_BASE}/api/results/{task_id}")
        if response.status_code == 200:
            results = response.json()
            print("✅ 结果获取成功")
            
            if "results" in results:
                result_data = results["results"]
                if "summary" in result_data:
                    summaries = result_data["summary"].get("summaries", [])
                    print(f"📝 生成了 {len(summaries)} 段摘要")
                if "multimodal_notes" in result_data:
                    notes = result_data["multimodal_notes"]
                    segments = notes.get("segments", [])
                    total_frames = notes.get("statistics", {}).get("total_frames", 0)
                    print(f"🎨 图文笔记: {len(segments)} 段, {total_frames} 帧")
            
            return True
        else:
            print(f"❌ 结果获取失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 结果获取异常: {e}")
        return False

def main():
    """完整的测试流程"""
    print("🧪 开始在线视频下载API测试...")
    
    # 测试视频URL（请替换为实际可用的URL）
    test_urls = [
        "https://www.youtube.com/watch?v=PQUcIbSEBCM",  # YouTube示例
        # "https://www.bilibili.com/video/BV1xx411c7mu",  # Bilibili示例
    ]
    
    # 1. 测试支持的平台
    if not test_supported_platforms():
        print("❌ 平台测试失败，请检查服务是否启动")
        return False
    
    print("\n" + "="*50 + "\n")
    
    # 如果没有提供测试URL，提示用户
    if not test_urls:
        print("⚠️ 请在脚本中添加测试URL后再运行完整测试")
        print("示例URL:")
        print("  YouTube: https://www.youtube.com/watch?v=VIDEO_ID")
        print("  Bilibili: https://www.bilibili.com/video/BV_ID")
        return True
    
    # 2. 测试每个URL
    for url in test_urls:
        print(f"🎯 测试URL: {url}")
        
        # 预览视频信息
        video_info = test_preview_video(url)
        if not video_info:
            continue
        
        print("\n" + "-"*30 + "\n")
        
        # 开始下载
        task_id = test_download_video(url)
        if not task_id:
            continue
        
        print("\n" + "-"*30 + "\n")
        
        # 监控进度
        success = test_monitor_progress(task_id)
        if not success:
            continue
        
        print("\n" + "-"*30 + "\n")
        
        # 获取结果
        test_get_results(task_id)
        
        print("\n" + "="*50 + "\n")
    
    print("🎉 测试完成！")
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("❌ 测试失败")
        exit(1)
    else:
        print("✅ 测试成功")
