#!/usr/bin/env python3
"""视频处理使用示例"""

from video_process import VideoProcessor,split_video
import sys

def main():
    if len(sys.argv)<2:
        print("用法: python example.py <视频文件路径或URL> [输出目录]")
        print("示例:")
        print("  python example.py video.mp4")
        print("  python example.py https://example.com/video.mp4 output/")
        return
    
    src=sys.argv[1]
    out_dir=sys.argv[2] if len(sys.argv)>2 else None
    
    try:
        print(f"处理视频: {src}")
        audio_file,video_file=split_video(src,out_dir)
        print(f"✓ 音频文件: {audio_file}")
        print(f"✓ 视频文件: {video_file}")
    except Exception as e:
        print(f"✗ 错误: {e}")

if __name__=="__main__":
    main()
