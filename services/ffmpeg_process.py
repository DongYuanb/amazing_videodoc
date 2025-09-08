import os,subprocess,tempfile,urllib.request,urllib.parse
from pathlib import Path
from typing import Union,Tuple,Optional,List

class VideoProcessor:
    """视频处理器：支持文件上传和链接解析，实现音视频分流"""

    def __init__(self,ffmpeg_path:str="ffmpeg"):
        self.ffmpeg=ffmpeg_path
        self._check_ffmpeg()

    def _check_ffmpeg(self):
        """检查ffmpeg可用性"""
        try:subprocess.run([self.ffmpeg,"-version"],capture_output=True,check=True)
        except:raise RuntimeError("ffmpeg not found")

    def _download_video(self,url:str,output_dir:str)->str:
        """下载视频到临时目录"""
        parsed=urllib.parse.urlparse(url)
        fname=Path(parsed.path).name or "video.mp4"
        if not fname.endswith(('.mp4','.avi','.mov','.mkv','.webm')):fname+=".mp4"

        output_path=os.path.join(output_dir,fname)
        urllib.request.urlretrieve(url,output_path)
        return output_path

    def _extract_streams(self,input_path:str,output_dir:str)->Tuple[str,str]:
        """提取音频和视频流"""
        base=Path(input_path).stem
        audio_out=os.path.join(output_dir,f"{base}_audio.wav")
        video_out=os.path.join(output_dir,f"{base}_video.mp4")

        # 提取音频流
        subprocess.run([
            self.ffmpeg, "-i", input_path,
            "-vn",                          # 忽略视频流
            "-acodec", "pcm_s16le",         # 使用 16-bit PCM 编码（标准 WAV 格式）
            "-ar", "44100",                 # 可选：设置采样率（如 44.1kHz）
            "-ac", "2",                     # 可选：设置声道数（立体声）
            "-y",                           # 覆盖输出文件
            audio_out                       # 输出 .wav 文件
        ], check=True, capture_output=True)

        # 提取视频流(无音频)
        subprocess.run([
            self.ffmpeg,"-i",input_path,"-an","-vcodec","copy",
            "-y",video_out
        ],check=True,capture_output=True)

        return audio_out,video_out

    def extract_frames(self, video_path: str, start_time: float, end_time: float,
                      fps: float = 1.0, output_dir: str = None) -> List[str]:
        """
        从视频指定时间范围抽取帧

        Args:
            video_path: 视频文件路径
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
            fps: 抽帧频率（每秒帧数）
            output_dir: 输出目录

        Returns:
            抽取的帧图片路径列表
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        if start_time >= end_time:
            raise ValueError("start_time must be less than end_time")

        # 创建输出目录
        if output_dir is None:
            output_dir = tempfile.mkdtemp(prefix="video_frames_")
        else:
            os.makedirs(output_dir, exist_ok=True)

        # 构建ffmpeg命令
        duration = end_time - start_time
        output_pattern = os.path.join(output_dir, "frame_%06d.jpg")

        cmd=[self.ffmpeg,"-ss",str(start_time),"-i",video_path,"-t",str(duration),"-vf",f"fps={fps},scale=-1:360","-q:v","5","-y",output_pattern]

        try:
            subprocess.run(cmd, capture_output=True, check=True, text=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"ffmpeg failed: {e.stderr}")

        # 获取生成的图片文件列表
        frame_files = []
        for file in sorted(os.listdir(output_dir)):
            if file.startswith("frame_") and file.endswith(".jpg"):
                frame_files.append(os.path.join(output_dir, file))

        if not frame_files:
            raise RuntimeError("No frames were extracted")

        return frame_files

    def process_file(self,file_path:str,output_dir:Optional[str]=None)->Tuple[str,str]:
        """处理本地视频文件"""
        if not os.path.exists(file_path):raise FileNotFoundError(f"File not found: {file_path}")

        out_dir=output_dir or os.path.dirname(file_path)
        os.makedirs(out_dir,exist_ok=True)

        return self._extract_streams(file_path,out_dir)

    def process_url(self,url:str,output_dir:Optional[str]=None)->Tuple[str,str]:
        """处理视频链接"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # 下载视频
            video_path=self._download_video(url,tmp_dir)

            # 设置输出目录
            out_dir=output_dir or os.getcwd()
            os.makedirs(out_dir,exist_ok=True)

            # 提取音视频流
            return self._extract_streams(video_path,out_dir)

    def process(self,source:Union[str,Path],output_dir:Optional[str]=None)->Tuple[str,str]:
        """统一处理接口：自动判断文件路径或URL"""
        src=str(source)
        if src.startswith(('http://','https://')):
            return self.process_url(src,output_dir)
        else:
            return self.process_file(src,output_dir)

def extract_audio_for_asr(video_path:str,output_audio:Optional[str]=None,ffmpeg_path:str="ffmpeg")->str:
    """便捷函数：从视频中提取适合ASR的音频格式"""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    if output_audio is None:
        output_audio=f"{Path(video_path).stem}_audio.wav"

    # ASR优化参数：16kHz单声道PCM格式
    cmd=[
        ffmpeg_path,"-i",video_path,
        "-vn","-acodec","pcm_s16le","-ar","16000","-ac","1",
        "-y",output_audio
    ]

    try:
        subprocess.run(cmd,capture_output=True,check=True,text=True)
        print(f"音频提取完成: {output_audio}")
        return output_audio
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"音频提取失败: {e.stderr}")

def split_video(source:Union[str,Path],output_dir:Optional[str]=None,ffmpeg_path:str="ffmpeg")->Tuple[str,str]:
    """便捷函数：分离音视频流"""
    processor=VideoProcessor(ffmpeg_path)
    return processor.process(source,output_dir)
