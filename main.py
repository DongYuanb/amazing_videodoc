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
from multimodal_note_generator import MultimodalNoteGenerator
from dotenv import load_dotenv
load_dotenv()
class VideoProcessingWorkflow:
    """视频处理工作流程编排器：专注于流程编排，功能模块解耦"""

    def __init__(self,
                 model_id:str="openrouter/horizon-beta",
                 ffmpeg_path:str="ffmpeg",
                 asr_appid:str=None,
                 asr_secret_id:str=None,
                 asr_secret_key:str=None,
                 jina_api_key:str=None,
                 enable_multimodal:bool=True):
        self.model_id=model_id
        self.enable_multimodal = enable_multimodal

        # 初始化各个功能模块
        self.ffmpeg_path = ffmpeg_path
        self.text_merger = TextMerger(model_id)
        self.summary_generator = Summarizer(model_id)
        self.asr_service = self._init_asr_service(asr_appid, asr_secret_id, asr_secret_key)

        # 初始化图文笔记生成器（如果启用）
        if self.enable_multimodal:
            self.multimodal_generator = self._init_multimodal_generator(jina_api_key, ffmpeg_path)

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

    def _init_multimodal_generator(self, jina_api_key, ffmpeg_path):
        """初始化图文笔记生成器"""
        if not jina_api_key:
            jina_api_key = os.getenv("JINA_API_KEY")

        print(f"🔧 检查 Jina API Key: {'已设置' if jina_api_key else '未设置'}")

        if not jina_api_key:
            print("⚠️  未提供 Jina API Key，将跳过图文笔记生成")
            return None

        try:
            print("🔧 正在初始化图文笔记生成器...")
            generator = MultimodalNoteGenerator(
                jina_api_key=jina_api_key,
                ffmpeg_path=ffmpeg_path
            )
            print("✅ 图文笔记生成器初始化成功")
            return generator
        except Exception as e:
            print(f"⚠️  图文笔记生成器初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return None

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
        else:
            raise RuntimeError("摘要生成失败")

    def generate_multimodal_notes(self, video_path:str, summary_json:str, output_dir:str)->Optional[str]:
        """生成图文混排笔记"""
        if not self.enable_multimodal or not self.multimodal_generator:
            print("⚠️  图文笔记生成功能未启用或初始化失败")
            return None

        try:
            notes_dir = os.path.join(output_dir, "multimodal_notes")
            notes_file = self.multimodal_generator.generate_multimodal_notes(
                video_path=video_path,
                summary_json_path=summary_json,
                output_dir=notes_dir
            )
            print(f"图文笔记生成完成: {notes_file}")
            return notes_file
        except Exception as e:
            print(f"⚠️  图文笔记生成失败: {e}")
            return None

    def process_from_existing(self,
                             video_path: str,
                             existing_output_dir: str,
                             start_from: str = "multimodal") -> Dict[str, str]:
        """
        从已有的输出目录继续处理

        Args:
            video_path: 原视频文件路径
            existing_output_dir: 已有的输出目录
            start_from: 从哪个步骤开始

        Returns:
            处理结果字典
        """
        if not os.path.exists(existing_output_dir):
            raise FileNotFoundError(f"输出目录不存在: {existing_output_dir}")

        # 检测已有文件
        existing_files = {}
        potential_files = {
            "audio": "audio.wav",
            "asr": "asr_result.json",
            "merged": "merged_text.json",
            "summary": "summary.json"
        }

        for key, filename in potential_files.items():
            file_path = os.path.join(existing_output_dir, filename)
            if os.path.exists(file_path):
                existing_files[key] = file_path
                print(f"✅ 发现已有文件: {key} -> {file_path}")

        if not existing_files:
            raise ValueError(f"在目录 {existing_output_dir} 中未找到任何可用的中间文件")

        return self.process_video(
            video_path=video_path,
            output_dir=existing_output_dir,
            start_from=start_from,
            existing_files=existing_files
        )


    def process_video(self,
                     video_path:str,
                     output_dir:Optional[str]=None,
                     keep_temp:bool=False,
                     start_from:str="audio_extract",
                     existing_files:Optional[Dict[str,str]]=None)->Dict[str,str]:
        """
        灵活的视频处理流程，支持从任意步骤开始

        Args:
            video_path: 视频文件路径
            output_dir: 输出目录
            keep_temp: 是否保留临时文件
            start_from: 从哪个步骤开始 ("audio_extract", "asr", "text_merge", "summary", "multimodal")
            existing_files: 已存在的文件路径字典，用于跳过前面的步骤
        """
        if output_dir is None:
            output_dir=f"output_{Path(video_path).stem}"

        os.makedirs(output_dir,exist_ok=True)

        print(f"🎬 开始处理视频: {video_path}")
        print(f"📁 输出目录: {output_dir}")
        print(f"🚀 从步骤开始: {start_from}")

        # 初始化文件路径（确保不为None）
        audio_path = existing_files.get("audio") if existing_files else os.path.join(output_dir,"audio.wav")
        asr_json = existing_files.get("asr") if existing_files else os.path.join(output_dir,"asr_result.json")
        merged_json = existing_files.get("merged") if existing_files else os.path.join(output_dir,"merged_text.json")
        summary_json = existing_files.get("summary") if existing_files else os.path.join(output_dir,"summary.json")

        # 如果从existing_files获取的路径为None，使用默认路径
        if audio_path is None:
            audio_path = os.path.join(output_dir,"audio.wav")
        if asr_json is None:
            asr_json = os.path.join(output_dir,"asr_result.json")
        if merged_json is None:
            merged_json = os.path.join(output_dir,"merged_text.json")
        if summary_json is None:
            summary_json = os.path.join(output_dir,"summary.json")

        multimodal_notes = None

        try:
            # 1. 提取音频
            if start_from == "audio_extract":
                print("\n1️⃣ 提取音频...")
                audio_path=self.extract_audio(video_path,audio_path)
            elif audio_path and os.path.exists(audio_path):
                print(f"✅ 跳过音频提取，使用现有文件: {audio_path}")

            # 2. ASR转录
            if start_from in ["audio_extract", "asr"]:
                print("\n2️⃣ ASR转录...")
                asr_json=self.run_asr(audio_path,asr_json)
            elif asr_json and os.path.exists(asr_json):
                print(f"✅ 跳过ASR转录，使用现有文件: {asr_json}")

            # 3. 文本合并
            if start_from in ["audio_extract", "asr", "text_merge"]:
                print("\n3️⃣ 文本合并...")
                merged_json=self.merge_texts(asr_json,merged_json)
            elif merged_json and os.path.exists(merged_json):
                print(f"✅ 跳过文本合并，使用现有文件: {merged_json}")

            # 4. 生成摘要
            if start_from in ["audio_extract", "asr", "text_merge", "summary"]:
                print("\n4️⃣ 生成摘要...")
                summary_json=self.generate_summary(merged_json,summary_json)
            elif summary_json and os.path.exists(summary_json):
                print(f"✅ 跳过摘要生成，使用现有文件: {summary_json}")
            else:
                # 如果是从multimodal开始，但没有summary文件，报错
                if start_from == "multimodal":
                    raise FileNotFoundError(f"图文笔记生成需要摘要文件，但文件不存在: {summary_json}")

            # 5. 生成图文混排笔记
            if self.enable_multimodal and start_from in ["audio_extract", "asr", "text_merge", "summary", "multimodal"]:
                print("\n5️⃣ 生成图文混排笔记...")
                multimodal_notes = self.generate_multimodal_notes(video_path, summary_json, output_dir)

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
                "summary":summary_json,
                "multimodal_notes":multimodal_notes
            }
            
            print(f"\n✅ 处理完成！")
            print(f"📄 ASR结果: {asr_json}")
            print(f"📝 合并文本: {merged_json}")
            print(f"📋 摘要: {summary_json}")
            if multimodal_notes:
                print(f"🎨 图文笔记: {multimodal_notes}")
            
            return result
            
        except Exception as e:
            print(f"\n❌ 处理失败: {e}")
            raise

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("🎬 视频处理工作流程")
        print("\n📋 用法:")
        print("  完整流程: python main.py <视频文件> [输出目录]")
        print("  从现有目录继续: python main.py --from-existing <视频文件> <已有输出目录> [开始步骤]")
        print("\n🚀 开始步骤选项:")
        print("  - audio_extract: 从音频提取开始（默认）")
        print("  - asr: 从ASR转录开始")
        print("  - text_merge: 从文本合并开始")
        print("  - summary: 从摘要生成开始")
        print("  - multimodal: 仅生成图文笔记")
        print("\n💡 示例:")
        print("  python main.py video.mp4")
        print("  python main.py video.mp4 my_output")
        print("  python main.py --from-existing video.mp4 output_demo2 multimodal")
        sys.exit(1)

    # 解析命令行参数
    if sys.argv[1] == "--from-existing":
        if len(sys.argv) < 4:
            print("❌ --from-existing 需要至少3个参数: 视频文件 已有输出目录 [开始步骤]")
            sys.exit(1)

        video_path = sys.argv[2]
        existing_dir = sys.argv[3]
        start_from = sys.argv[4] if len(sys.argv) > 4 else "multimodal"

        if not os.path.exists(video_path):
            print(f"❌ 视频文件不存在: {video_path}")
            sys.exit(1)

        try:
            workflow = VideoProcessingWorkflow()
            result = workflow.process_from_existing(video_path, existing_dir, start_from)
        except Exception as e:
            print(f"❌ 处理失败: {e}")
            sys.exit(1)

    else:
        # 常规处理流程
        video_path = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else None

        if not os.path.exists(video_path):
            print(f"❌ 视频文件不存在: {video_path}")
            sys.exit(1)

        try:
            workflow = VideoProcessingWorkflow()
            result = workflow.process_video(video_path, output_dir, keep_temp=False)
        except Exception as e:
            print(f"❌ 处理失败: {e}")
            sys.exit(1)

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

if __name__=="__main__":
    main()
