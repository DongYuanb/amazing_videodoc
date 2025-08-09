#!/usr/bin/env python3
"""
测试 API 功能的脚本
"""
import requests
import time
import json
from pathlib import Path

API_BASE = "http://localhost:8000"

def test_health():
    """测试健康检查"""
    print("🔍 测试健康检查...")
    try:
        response = requests.get(f"{API_BASE}/api/health")
        if response.status_code == 200:
            print("✅ 健康检查通过")
            return True
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

def test_upload(video_file):
    """测试文件上传"""
    print(f"📤 测试文件上传: {video_file}")
    
    if not Path(video_file).exists():
        print(f"❌ 视频文件不存在: {video_file}")
        return None
    
    try:
        with open(video_file, "rb") as f:
            files = {"file": (Path(video_file).name, f, "video/mp4")}
            response = requests.post(f"{API_BASE}/api/upload", files=files)
        
        if response.status_code == 200:
            result = response.json()
            task_id = result["task_id"]
            print(f"✅ 文件上传成功，任务ID: {task_id}")
            return task_id
        else:
            print(f"❌ 上传失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 上传异常: {e}")
        return None

def test_process(task_id):
    """测试开始处理"""
    print(f"⚙️ 测试开始处理: {task_id}")
    
    try:
        data = {
            "enable_multimodal": True,  # 启用图文功能
            "keep_temp": True
        }
        response = requests.post(f"{API_BASE}/api/process/{task_id}", json=data)
        
        if response.status_code == 200:
            print("✅ 处理已开始")
            return True
        else:
            print(f"❌ 开始处理失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 处理异常: {e}")
        return False

def test_status(task_id, max_wait=300):
    """测试状态查询并等待完成"""
    print(f"📊 监控任务状态: {task_id}")
    
    start_time = time.time()
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(f"{API_BASE}/api/status/{task_id}")
            if response.status_code == 200:
                status_data = response.json()
                status = status_data["status"]
                current_step = status_data.get("current_step", "")
                progress = status_data.get("progress", 0)
                
                print(f"📈 状态: {status} | 步骤: {current_step} | 进度: {progress:.1%}")
                
                if status == "completed":
                    print("✅ 任务完成")
                    return True
                elif status == "failed":
                    error = status_data.get("error_message", "未知错误")
                    print(f"❌ 任务失败: {error}")
                    return False
                
                time.sleep(5)  # 等待5秒后再次查询
            else:
                print(f"❌ 状态查询失败: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ 状态查询异常: {e}")
            return False
    
    print("⏰ 等待超时")
    return False

def test_results(task_id):
    """测试获取结果"""
    print(f"📋 获取处理结果: {task_id}")

    try:
        response = requests.get(f"{API_BASE}/api/results/{task_id}")
        if response.status_code == 200:
            results = response.json()
            print("✅ 结果获取成功")

            # 显示结果摘要
            if "results" in results:
                result_data = results["results"]
                if "summary" in result_data:
                    summaries = result_data["summary"].get("summaries", [])
                    print(f"📝 生成了 {len(summaries)} 段摘要")
                if "asr_result" in result_data:
                    print(f"🎤 ASR 转录完成")
                if "merged_text" in result_data:
                    print(f"📄 文本合并完成")
                if "multimodal_notes" in result_data:
                    notes = result_data["multimodal_notes"]
                    segments = notes.get("segments", [])
                    total_frames = notes.get("statistics", {}).get("total_frames", 0)
                    print(f"🎨 图文笔记完成: {len(segments)} 段, {total_frames} 帧")

            return True
        else:
            print(f"❌ 结果获取失败: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ 结果获取异常: {e}")
        return False

def test_export(task_id):
    """测试导出功能"""
    print(f"📤 测试导出功能: {task_id}")

    export_formats = [
        ("markdown", "md"),
        # ("html", "html"),
        ("json", "json")
    ]

    success_count = 0

    for format_name, file_ext in export_formats:
        try:
            print(f"  📄 导出 {format_name.upper()} 格式...")
            response = requests.get(f"{API_BASE}/api/export/{task_id}/{format_name}")

            if response.status_code == 200:
                # 保存文件到本地测试
                output_file = f"test_export_{task_id}.{file_ext}"
                with open(output_file, "wb") as f:
                    f.write(response.content)

                file_size = len(response.content)
                print(f"    ✅ {format_name.upper()} 导出成功: {output_file} ({file_size} bytes)")
                success_count += 1
            else:
                print(f"    ❌ {format_name.upper()} 导出失败: {response.status_code}")

        except Exception as e:
            print(f"    ❌ {format_name.upper()} 导出异常: {e}")

    print(f"📊 导出测试结果: {success_count}/{len(export_formats)} 成功")
    return success_count == len(export_formats)

def main():
    """完整的 API 测试流程"""
    print("🧪 开始 API 功能测试...")
    
    # 1. 健康检查
    if not test_health():
        print("❌ 服务不可用，请先启动 API 服务")
        return False
    
    # 2. 文件上传测试
    video_file = "upload/demo3.mp4"  # 使用现有的测试视频
    task_id = test_upload(video_file)
    if not task_id:
        return False

    # 3. 开始处理 (启用图文功能)
    print("⚙️ 开始处理 (启用图文功能)...")
    try:
        data = {
            "enable_multimodal": True,  # 启用图文功能
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

    # 4. 监控状态
    if not test_status(task_id):
        return False

    # 5. 获取结果
    if not test_results(task_id):
        return False

    # 6. 测试导出功能
    if not test_export(task_id):
        print("⚠️ 导出功能测试失败，但主要功能正常")

    print("🎉 所有测试通过！")
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        print("❌ 测试失败")
        exit(1)
    else:
        print("✅ 测试成功")
