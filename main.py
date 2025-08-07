#!/usr/bin/env python3
"""
视频处理工作流程编排器：音频提取 -> ASR转录 -> 文本合并 -> 摘要生成
"""
import os,sys,json
from pathlib import Path
from typing import Optional,Dict
from asr_tencent.text_merge import TextMerger
from asr_tencent.summary_generator import Summarizer
from asr_tencent.asr_service import ASRService
from ffmpeg_process import extract_audio_for_asr
from dotenv import load_dotenv
load_dotenv()
class VideoProcessingWorkflow:
    """视频处理工作流程编排器：专注于流程编排，功能模块解耦"""

    def __init__(self,
                 model_id:str="openrouter/horizon-beta",
                 ffmpeg_path:str="ffmpeg",
                 asr_appid:str=None,
                 asr_secret_id:str=None,
                 asr_secret_key:str=None):
        self.model_id=model_id

        # 初始化各个功能模块
        self.ffmpeg_path = ffmpeg_path
        self.text_merger = TextMerger(model_id)
        self.summary_generator = Summarizer(model_id)
        self.asr_service = self._init_asr_service(asr_appid, asr_secret_id, asr_secret_key)

    def _init_asr_service(self, appid, secret_id, secret_key):
        """初始化 ASR 服务"""
        # 如果没有提供参数，尝试从环境变量或默认值获取
        if not appid:
            appid = os.getenv("TENCENT_APPID")
        if not secret_id:
            secret_id = os.getenv("TENCENT_SECRET_ID")
        if not secret_key:
            secret_key = os.getenv("TENCENT_SECRET_KEY")

        try:
            return ASRService(appid, secret_id, secret_key)
        except ValueError as e:
            raise RuntimeError(f"ASR服务初始化失败: {e}")

    def extract_audio(self,video_path:str,output_audio:Optional[str]=None)->str:
        """从视频中提取音频（委托给ffmpeg_process模块）"""
        return extract_audio_for_asr(video_path, output_audio, self.ffmpeg_path)
    
    def run_asr(self,audio_path:str,output_json:Optional[str]=None)->str:
        """运行ASR转录（使用ASR服务模块）"""
        if output_json is None:
            output_json=f"{Path(audio_path).stem}_asr.json"

        try:
            return self.asr_service.transcribe_audio(audio_path, output_json)
        except Exception as e:
            raise RuntimeError(f"ASR转录失败: {e}")
    
    def merge_texts(self,asr_json:str,output_merged:Optional[str]=None)->str:
        """合并ASR文本"""
        if output_merged is None:
            output_merged=f"{Path(asr_json).stem}_merged.json"
        
        if self.text_merger.process_file(asr_json,output_merged):
            print(f"文本合并完成: {output_merged}")
            return output_merged
        else:
            raise RuntimeError("文本合并失败")
    
    def generate_summary(self,merged_json:str,output_summary:Optional[str]=None)->str:
        """生成摘要"""
        if output_summary is None:
            output_summary=f"{Path(merged_json).stem}_summary.json"
        
        if self.summary_generator.process_file(merged_json,output_summary):
            print(f"摘要生成完成: {output_summary}")
            return output_summary

    
    def process_video(self,video_path:str,output_dir:Optional[str]=None,keep_temp:bool=False)->Dict[str,str]:
        """完整的视频处理流程"""
        if output_dir is None:
            output_dir=f"output_{Path(video_path).stem}"
        
        os.makedirs(output_dir,exist_ok=True)
        
        print(f"🎬 开始处理视频: {video_path}")
        print(f"📁 输出目录: {output_dir}")
        
        try:
            # 1. 提取音频
            print("\n1️⃣ 提取音频...")
            audio_path=self.extract_audio(video_path,os.path.join(output_dir,"audio.wav"))
            
            # 2. ASR转录
            print("\n2️⃣ ASR转录...")
            asr_json=self.run_asr(audio_path,os.path.join(output_dir,"asr_result.json"))
            
            # 3. 文本合并
            print("\n3️⃣ 文本合并...")
            merged_json=self.merge_texts(asr_json,os.path.join(output_dir,"merged_text.json"))
            
            # 4. 生成摘要
            print("\n4️⃣ 生成摘要...")
            summary_json=self.generate_summary(merged_json,os.path.join(output_dir,"summary.json"))
            
            # 清理临时文件
            if not keep_temp:
                try:
                    os.unlink(audio_path)
                    print("🧹 清理临时音频文件")
                except:pass
            
            result={
                "video_path":video_path,
                "output_dir":output_dir,
                "asr_result":asr_json,
                "merged_text":merged_json,
                "summary":summary_json
            }
            
            print(f"\n✅ 处理完成！")
            print(f"📄 ASR结果: {asr_json}")
            print(f"📝 合并文本: {merged_json}")
            print(f"📋 摘要: {summary_json}")
            
            return result
            
        except Exception as e:
            print(f"\n❌ 处理失败: {e}")
            raise

def main():
    """主函数"""
    if len(sys.argv)<2:
        print("用法: python main.py <视频文件路径> [输出目录]")
        print("示例: python main.py video.mp4")
        print("示例: python main.py video.mp4 output_folder")
        sys.exit(1)
    
    video_path=sys.argv[1]
    output_dir=sys.argv[2] if len(sys.argv)>2 else None
    
    if not os.path.exists(video_path):
        print(f"❌ 视频文件不存在: {video_path}")
        sys.exit(1)
    
    try:
        workflow=VideoProcessingWorkflow()
        result=workflow.process_video(video_path,output_dir,keep_temp=False)
        
        # 显示摘要预览
        try:
            with open(result["summary"],'r',encoding='utf-8') as f:
                summary_data=json.load(f)
                summaries=summary_data.get("summaries",[])
                
            print(f"\n📋 摘要预览 ({len(summaries)}段):")
            for i,s in enumerate(summaries[:3]):  # 只显示前3段
                start=s.get("start_time","")
                end=s.get("end_time","")
                summary=s.get("summary","")[:100]+"..." if len(s.get("summary",""))>100 else s.get("summary","")
                print(f"  {i+1}. [{start}-{end}] {summary}")
            
            if len(summaries)>3:
                print(f"  ... 还有 {len(summaries)-3} 段摘要")
                
        except Exception as e:
            print(f"摘要预览失败: {e}")
        
        print(f"\n🎉 全部完成！结果保存在: {result['output_dir']}")
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        sys.exit(1)

if __name__=="__main__":
    main()
