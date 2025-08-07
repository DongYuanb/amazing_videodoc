import json
import os
import sys
from typing import List, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

class Summarizer:
    """会议内容整理工具（按原始时间段）"""
    
    def __init__(self, model_id: str):
        """初始化总结器，使用OpenAI客户端"""
        self.model_id = model_id
        self.client = self._init_openai_client()
        
    def _init_openai_client(self) -> OpenAI:
        """初始化OpenAI风格客户端"""
        api_key = os.environ.get("ARK_API_KEY")
        if not api_key:
            raise ValueError("请设置环境变量 ARK_API_KEY 存储API密钥")
            
        return OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )

    def load_timed_texts(self, file_path: str) -> List[Dict[str, Any]]:
        """
        加载包含时间戳的文本数据。
        能智能处理根节点是列表 `[...]` 或被包装的对象 `{"key": [...]}` 的情况。
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"输入文件不存在: {file_path}")
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 检查数据是字典还是列表
            sentence_list = []
            if isinstance(data, list):
                # 如果根节点就是列表，直接使用
                sentence_list = data
            elif isinstance(data, dict):
                # 如果是字典，遍历它的值，找到第一个是列表的值
                for value in data.values():
                    if isinstance(value, list):
                        sentence_list = value
                        break
            
            if not sentence_list:
                print("在JSON文件中未找到有效的句子列表。")
                return []

            # 验证并提取数据
            valid_data = []
            for item in sentence_list:
                # 确保item是字典且包含所需键
                if isinstance(item, dict) and "start_time" in item and "text" in item:
                    valid_data.append(item)
            
            print(f"成功加载 {len(valid_data)} 条有效文本数据")
            return valid_data
            
        except json.JSONDecodeError:
            raise ValueError(f"文件格式错误，无法解析JSON: {file_path}")
        except Exception as e:
            raise IOError(f"读取文件时发生错误: {file_path}, 错误: {e}")

    def generate_segment_summary(self, segment: Dict[str, Any]) -> Dict[str, Any]:
        """对单个时间段内容进行整理总结"""
        start_time = segment.get("start_time")
        end_time = segment.get("end_time")
        content = segment.get("text", "")
        if not content:
            summary = "该时间段无有效内容"
        else:
            prompt = f"""
请将以下会议内容整理为正式会议纪要：

### 内容处理要求
1. **去冗余**：彻底删除口语化表达（如“嗯”“对吧”“你知道”）、重复表述及无意义填充词
2. **抓核心**：精准提炼3-5个关键信息点（如结论、决策、重要观点、数据等）
3. **保完整**：确保保留所有必要信息，不遗漏任何实质性内容

### 格式输出要求
1. **结构框架**：采用“核心要点+具体说明”的层级结构，先用一句话总述该时间段核心内容，再分点展开关键信息
2. **分点规范**：使用数字序号（1. 2. 3.）列举关键信息，每点不超过2句话，语言精炼
3. **语言风格**：采用第三人称书面语，避免主观表述（如“我认为”“我们觉得”），用词严谨客观
4. **排版美观**：段落清晰（总述单独成段，分点另起行），无多余空行或标点

会议内容：
{content}
"""
            try:
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
                    stream=False
                )
                summary = completion.choices[0].message.content.strip()
            except Exception as e:
                summary = f"生成总结失败: {str(e)}"
        return {
            "start_time": start_time,
            "end_time": end_time,
            "summary": summary
        }

    def process_meeting(self, input_path: str, output_path: str) -> None:
        """加载→逐条整理→保存"""
        try:
            timed_texts = self.load_timed_texts(input_path)
            if not timed_texts:
                print("没有有效文本数据可处理", file=sys.stderr)
                return

            print(f"共 {len(timed_texts)} 个时间段，逐条整理中...")
            summaries = []
            for idx, segment in enumerate(timed_texts):
                print(f"正在处理第 {idx+1} 条（{segment.get('start_time')} ~ {segment.get('end_time')}）...")
                summary_item = self.generate_segment_summary(segment)
                summaries.append(summary_item)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(summaries, f, ensure_ascii=False, indent=4)

            print(f"处理完成，总结已保存至 {output_path}")

        except Exception as e:
            print(f"处理失败: {str(e)}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    INPUT_FILE = "2.json"    # 输入文件
    OUTPUT_FILE = "3.json"  # 输出文件
    MODEL_ID = "openrouter/horizon-beta"  # 模型ID（与OpenAI调用示例一致）
    
    try:
        summarizer = Summarizer(MODEL_ID)
        summarizer.process_meeting(INPUT_FILE, OUTPUT_FILE)
    except Exception as e:
        print(f"程序错误: {str(e)}", file=sys.stderr)
        sys.exit(1)
