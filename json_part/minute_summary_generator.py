import json
import os
import sys
from typing import List, Dict, Any
from openai import OpenAI

class DoubaoMinuteSummarizer:
    """基于OpenAI风格API的分钟级会议总结工具"""
    
    def __init__(self, model_id: str):
        """初始化总结器，使用OpenAI客户端"""
        self.model_id = model_id
        self.client = self._init_openai_client()
        
    def _init_openai_client(self) -> OpenAI:
        """初始化OpenAI风格客户端"""
        api_key = os.environ.get("ARK_API_KEY")
        if not api_key:
            raise ValueError("请设置环境变量 ARK_API_KEY 存储API密钥")
            
        # 初始化OpenAI客户端，指向豆包API端点
        return OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=api_key
        )

    def load_timed_texts(self, file_path: str) -> List[Dict[str, Any]]:
        """加载包含时间戳的文本数据"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"输入文件不存在: {file_path}")
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # 验证数据格式
            valid_data = []
            for item in data:
                if isinstance(item, dict) and "start_time" in item and "text" in item:
                    valid_data.append({
                        "start_time": int(item["start_time"]),
                        "text": str(item["text"]).strip()
                    })
            
            print(f"成功加载 {len(valid_data)} 条有效文本数据")
            return valid_data
            
        except json.JSONDecodeError:
            raise ValueError("输入文件不是有效的JSON格式")
        except Exception as e:
            raise RuntimeError(f"加载数据失败: {str(e)}")

    def group_by_minute(self, texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将文本按分钟分组并合并内容"""
        minute_content = {}
        
        for item in texts:
            minute = item["start_time"] // 60000  # 毫秒转分钟
            if minute in minute_content:
                minute_content[minute] += " " + item["text"]
            else:
                minute_content[minute] = item["text"]
        
        # 按分钟排序并格式化
        return [
            {
                "minute": minute,
                "content": content.strip()
            } 
            for minute, content in sorted(minute_content.items())
        ]

    def generate_minute_summary(self, minute: int, content: str) -> str:
        """调用API生成单分钟内容的总结（OpenAI风格）"""
        if not content:
            return "该分钟无有效内容"
            
        # 构建提示词
        prompt = f"""
        请将以下第 {minute} 分钟的会议内容整理为正式会议纪要：
        
       ### 内容处理要求
1. **去冗余**：彻底删除口语化表达（如“嗯”“对吧”“你知道”）、重复表述及无意义填充词
2. **抓核心**：精准提炼3-5个关键信息点（如结论、决策、重要观点、数据等）
3. **保完整**：确保保留所有必要信息，不遗漏任何实质性内容

### 格式输出要求
1. **结构框架**：采用“核心要点+具体说明”的层级结构，先用一句话总述该分钟核心内容，再分点展开关键信息
2. **分点规范**：使用数字序号（1. 2. 3.）列举关键信息，每点不超过2句话，语言精炼
3. **语言风格**：采用第三人称书面语，避免主观表述（如“我认为”“我们觉得”），用词严谨客观
4. **排版美观**：段落清晰（总述单独成段，分点另起行），无多余空行或标点

        会议内容：
        {content}
        """
        
        try:
            # OpenAI风格API调用
            completion = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {
                        "role": "system",
                        "content": "你是专业会议记录员，擅长将口语化内容转化为正式纪要。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                stream=False  # 非流式返回
            )
            
            return completion.choices[0].message.content.strip()
            
        except Exception as e:
            return f"生成总结失败: {str(e)}"

    def process_meeting(self, input_path: str, output_path: str) -> None:
        """完整处理流程：加载→分组→生成总结→保存"""
        try:
            # 1. 加载带时间戳的文本
            timed_texts = self.load_timed_texts(input_path)
            if not timed_texts:
                print("没有有效文本数据可处理", file=sys.stderr)
                return
            
            # 2. 按分钟分组
            minute_groups = self.group_by_minute(timed_texts)
            print(f"已按分钟分组，共 {len(minute_groups)} 个时间段")
            
            # 3. 生成每个分钟的总结
            summaries = []
            for group in minute_groups:
                minute = group["minute"]
                print(f"正在处理第 {minute} 分钟...")
                summary = self.generate_minute_summary(minute, group["content"])
                summaries.append({
                    "minute": minute,
                    "summary": summary
                })
            
            # 4. 保存结果
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(summaries, f, ensure_ascii=False, indent=4)
            
            print(f"处理完成，总结已保存至 {output_path}")
            
        except Exception as e:
            print(f"处理失败: {str(e)}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    # 配置参数（与OpenAI风格API匹配）
    INPUT_FILE = "test.json"    # 输入文件
    OUTPUT_FILE = "minute_summaries.json"  # 输出文件
    MODEL_ID = "kimi-k2-250711"  # 模型ID（与OpenAI调用示例一致）
    
    try:
        summarizer = DoubaoMinuteSummarizer(MODEL_ID)
        summarizer.process_meeting(INPUT_FILE, OUTPUT_FILE)
    except Exception as e:
        print(f"程序错误: {str(e)}", file=sys.stderr)
        sys.exit(1)