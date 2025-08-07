#!/usr/bin/env python3
"""
测试进度回调功能
"""
import requests
import time
import json
from pathlib import Path

API_BASE = "http://localhost:8000"

def test_progress_monitoring():
    """测试进度监控功能"""
    print("🧪 测试进度监控功能...")
    
    # 1. 上传视频
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
    
    # 2. 开始处理
    print("⚙️ 开始处理...")
    try:
        data = {
            "start_from": "audio_extract",
            "enable_multimodal": False,  # 先测试基础功能
            "keep_temp": True
        }
        response = requests.post(f"{API_BASE}/api/process/{task_id}", json=data)
        
        if response.status_code != 200:
            print(f"❌ 开始处理失败: {response.status_code}")
            return False
        
        print("✅ 处理已开始")
    except Exception as e:
        print(f"❌ 处理异常: {e}")
        return False
    
    # 3. 详细监控进度
    print("📊 详细监控进度...")
    
    progress_history = []
    start_time = time.time()
    max_wait = 300  # 5分钟超时
    
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
            
            # 记录进度变化
            current_info = {
                "timestamp": time.time() - start_time,
                "status": status,
                "step": current_step,
                "progress": progress
            }
            
            # 只在进度有变化时记录
            if not progress_history or (
                progress_history[-1]["step"] != current_step or 
                abs(progress_history[-1]["progress"] - progress) > 0.01
            ):
                progress_history.append(current_info)
                elapsed = current_info["timestamp"]
                print(f"  [{elapsed:6.1f}s] {status:12} | {current_step:20} | {progress:6.1%}")
            
            if status == "completed":
                print("✅ 任务完成")
                break
            elif status == "failed":
                error = status_data.get("error_message", "未知错误")
                print(f"❌ 任务失败: {error}")
                break
            
            time.sleep(2)  # 每2秒查询一次
            
        except Exception as e:
            print(f"❌ 状态查询异常: {e}")
            break
    
    # 4. 分析进度历史
    print(f"\n📈 进度分析 (共 {len(progress_history)} 个状态变化):")
    
    if progress_history:
        total_time = progress_history[-1]["timestamp"]
        print(f"  总耗时: {total_time:.1f} 秒")
        
        # 按步骤分组
        steps = {}
        for entry in progress_history:
            step = entry["step"]
            if step not in steps:
                steps[step] = []
            steps[step].append(entry)
        
        print(f"  处理步骤:")
        for step, entries in steps.items():
            if entries:
                start_time = entries[0]["timestamp"]
                end_time = entries[-1]["timestamp"]
                duration = end_time - start_time
                print(f"    {step:20}: {duration:6.1f}s")
        
        # 检查进度回调是否工作
        has_detailed_progress = any(
            "asr" in entry["step"] or 
            "text_merge" in entry["step"] or 
            "summary" in entry["step"] 
            for entry in progress_history
        )
        
        if has_detailed_progress:
            print("✅ 详细进度回调正常工作")
        else:
            print("⚠️  未检测到详细进度回调")
    
    return len(progress_history) > 0

def test_service_status():
    """测试服务状态接口"""
    print("\n🔍 测试服务状态...")
    
    try:
        response = requests.get(f"{API_BASE}/api/health")
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ 服务健康: {health_data}")
            return True
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 健康检查异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始进度回调功能测试...")
    
    # 测试服务状态
    if not test_service_status():
        return False
    
    # 测试进度监控
    if not test_progress_monitoring():
        return False
    
    print("\n🎉 进度回调功能测试完成！")
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
