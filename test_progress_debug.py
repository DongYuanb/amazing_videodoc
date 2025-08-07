#!/usr/bin/env python3
"""
调试进度回调功能
"""
import requests
import time
import json
from pathlib import Path

API_BASE = "http://localhost:8000"

def test_simple_progress():
    """简单的进度测试"""
    print("🧪 简单进度测试...")
    
    # 1. 上传小视频文件
    video_file = "upload/demo3.mp4"
    if not Path(video_file).exists():
        print(f"❌ 测试视频不存在: {video_file}")
        return False
    
    print(f"📤 上传视频: {video_file}")
    try:
        with open(video_file, "rb") as f:
            files = {"file": (Path(video_file).name, f, "video/mp4")}
            response = requests.post(f"{API_BASE}/api/upload", files=files)
        
        if response.status_code != 200:
            print(f"❌ 上传失败: {response.status_code}")
            return False
        
        task_id = response.json()["task_id"]
        print(f"✅ 上传成功，任务ID: {task_id}")
    except Exception as e:
        print(f"❌ 上传异常: {e}")
        return False
    
    # 2. 开始处理（从音频提取开始，不做图文）
    print("⚙️ 开始处理（音频提取+ASR+文本合并+摘要）...")
    try:
        data = {
            "start_from": "audio_extract",  # 从音频提取开始
            "enable_multimodal": False,  # 不做图文笔记
            "keep_temp": True
        }
        response = requests.post(f"{API_BASE}/api/process/{task_id}", json=data)
        
        if response.status_code != 200:
            print(f"❌ 开始处理失败: {response.status_code} - {response.text}")
            return False
        
        print("✅ 处理已开始")
    except Exception as e:
        print(f"❌ 处理异常: {e}")
        return False
    
    # 3. 快速监控进度（每秒查询）
    print("📊 快速监控进度...")
    
    start_time = time.time()
    max_wait = 120  # 2分钟超时
    last_status = None
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{API_BASE}/api/status/{task_id}")
            if response.status_code != 200:
                print(f"❌ 状态查询失败: {response.status_code}")
                break
            
            status_data = response.json()
            status = status_data["status"]
            current_step = status_data.get("current_step", "")
            progress = status_data.get("progress", 0)
            
            # 显示状态变化
            current_status = f"{status}|{current_step}|{progress:.1%}"
            if current_status != last_status:
                elapsed = time.time() - start_time
                print(f"  [{elapsed:6.1f}s] {status:12} | {current_step:20} | {progress:6.1%}")
                last_status = current_status
            
            if status == "completed":
                print("✅ 任务完成")
                return True
            elif status == "failed":
                error = status_data.get("error_message", "未知错误")
                print(f"❌ 任务失败: {error}")
                return False
            
            time.sleep(1)  # 每秒查询一次
            
        except Exception as e:
            print(f"❌ 状态查询异常: {e}")
            break
    
    print("⏰ 等待超时")
    return False

def check_server_logs():
    """提示检查服务器日志"""
    print("\n💡 调试建议:")
    print("1. 检查 API 服务器的控制台输出")
    print("2. 查看是否有 '🔄 进度更新' 和 '📞 调用进度回调' 的调试信息")
    print("3. 如果没有看到这些信息，说明进度回调没有被调用")
    print("4. 如果看到了但状态没更新，说明状态更新有问题")

def main():
    """主测试函数"""
    print("🚀 开始进度回调调试测试...")
    
    # 检查服务状态
    try:
        response = requests.get(f"{API_BASE}/api/health")
        if response.status_code != 200:
            print("❌ 服务不可用")
            return False
        print("✅ 服务正常")
    except:
        print("❌ 无法连接到服务")
        return False
    
    # 运行简单测试
    success = test_simple_progress()
    
    # 显示调试建议
    check_server_logs()
    
    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
