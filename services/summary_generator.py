import json
import os
import sys
import asyncio
import logging
from typing import List, Dict, Any, AsyncGenerator, Optional
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

class Summarizer:
    """会议内容整理工具（按原始时间段）"""
    
    def __init__(self, model_id: str, logger: Optional[logging.Logger] = None):
        """初始化总结器，使用OpenAI客户端"""
        self.model_id = model_id
        self.logger = logger or logging.getLogger(__name__)
        self.client = self._init_openai_client()
        
    def _init_openai_client(self) -> OpenAI:
        """初始化OpenAI风格客户端"""
        api_key = os.environ.get("OPENAI_API_KEY")
        base_url = os.environ.get("OPENAI_BASE_URL")
        if not api_key:
            raise ValueError("请设置环境变量 OPENAI_API_KEY 存储API密钥")
            
        return OpenAI(
            base_url=base_url,
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
                self.logger.warning("在JSON文件中未找到有效的句子列表")
                return []

            # 验证并提取数据
            valid_data = []
            for item in sentence_list:
                # 确保item是字典且包含所需键
                if isinstance(item, dict) and "start_time" in item and "text" in item:
                    valid_data.append(item)

            self.logger.info(f"成功加载 {len(valid_data)} 条有效文本数据")
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
请将以下视频内容整理为摘要：

### 内容处理要求
1. **去冗余**：删除口语化表达（如“嗯”“对吧”“你知道”）、重复表述及无意义填充词
2. **抓核心**：精准提炼2-3个关键信息点（如结论、决策、重要观点、数据等）
3. **保完整**：确保保留所有必要信息，不遗漏任何实质性内容

### 格式输出要求
1. **结构框架**：采用“核心要点+具体说明”的层级结构，先用一句话总述该时间段核心内容，再分点展开关键信息
2. **分点规范**：使用数字序号（1. 2. 3.）列举关键信息，每点不超过2句话，语言精炼
3. **语言风格**：采用第三人称书面语，避免主观表述（如“我认为”“我们觉得”），用词严谨客观
4. **排版美观**：段落清晰（总述单独成段，分点另起行），无多余空行或标点

视频内容：
{content}
"""
            try:
                completion = self.client.chat.completions.create(
                    model=self.model_id,
                    messages=[
                        {
                            "role": "system",
                            "content": "你擅长将口播内容转化为内容摘要。"
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

    def process_file(self, input_path: str, output_path: str) -> bool:
        """加载→逐条整理→保存，返回成功状态"""
        try:
            timed_texts = self.load_timed_texts(input_path)
            if not timed_texts:
                self.logger.error("没有有效文本数据可处理")
                return False

            self.logger.info(f"共 {len(timed_texts)} 个时间段，开始逐条整理...")
            summaries = []
            for idx, segment in enumerate(timed_texts):
                self.logger.info(f"正在处理第 {idx+1}/{len(timed_texts)} 条（{segment.get('start_time')} ~ {segment.get('end_time')}）")
                summary_item = self.generate_segment_summary(segment)
                summaries.append(summary_item)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({"summaries": summaries}, f, ensure_ascii=False, indent=4)

            self.logger.info(f"处理完成，总结已保存至 {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"处理失败: {str(e)}")
            return False

    async def process_file_async(self, input_path: str, output_path: str) -> bool:
        """异步处理文件"""
        try:
            # 在线程池中执行同步方法
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.process_file,
                input_path,
                output_path
            )
            return result
        except Exception as e:
            raise RuntimeError(f"摘要生成失败: {e}")

    def load_asr_content(self, asr_file_path: str) -> str:
        """加载ASR结果并拼接成完整文本"""
        try:
            with open(asr_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 处理不同的ASR结果格式
            sentences = []
            if isinstance(data, list):
                sentences = data
            elif isinstance(data, dict):
                sentences = data.get("result_sentences", [])

            if not sentences:
                self.logger.warning("ASR文件中没有找到有效的句子数据")
                return ""

            # 拼接所有文本
            full_text = " ".join([item.get("text", "").strip() for item in sentences if item.get("text", "").strip()])
            self.logger.info(f"成功加载ASR内容，总长度: {len(full_text)} 字符")
            return full_text

        except Exception as e:
            self.logger.error(f"加载ASR文件失败: {e}")
            return ""

    async def generate_full_summary_stream(self, asr_file_path: str) -> AsyncGenerator[str, None]:
        """基于ASR结果生成流式全文摘要"""
        full_text = self.load_asr_content(asr_file_path)
        if not full_text:
            yield "无法获取视频内容，请稍后重试。"
            return

        prompt = f"""
请为以下视频内容生成一个简洁的摘要：

### 摘要要求
1. **核心内容**：提炼视频的主要观点和关键信息
2. **结构清晰**：使用要点形式，便于快速阅读
3. **语言精炼**：避免冗余，突出重点

### 视频内容
{full_text}

请生成摘要：
"""

        try:
            self.logger.info("开始生成流式全文摘要")
            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": "你是一个专业的内容摘要助手，擅长提炼视频内容的核心要点。"},
                    {"role": "user", "content": prompt}
                ],
                stream=True,
                temperature=0.3,
                max_tokens=1000
            )

            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            self.logger.error(f"生成流式摘要失败: {e}")
            yield f"摘要生成失败: {str(e)}"

    async def generate_full_summary(self, asr_file_path: str, output_path: str = None) -> str:
        """保存完整的全文摘要（非流式版本）"""
        full_text = self.load_asr_content(asr_file_path)
        if not full_text:
            return "无法获取视频内容"

        # 收集流式输出
        summary_parts = []
        async for chunk in self.generate_full_summary_stream(asr_file_path):
            summary_parts.append(chunk)

        full_summary = "".join(summary_parts)

        # 如果指定了输出路径，保存到文件
        if output_path:
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        "full_summary": full_summary,
                        "generated_at": asyncio.get_event_loop().time(),
                        "source_file": asr_file_path
                    }, f, ensure_ascii=False, indent=2)
                self.logger.info(f"全文摘要已保存到: {output_path}")
            except Exception as e:
                self.logger.error(f"保存摘要文件失败: {e}")

        return full_summary

    def get_service_status(self) -> dict:
        """获取服务状态"""
        return {
            "service": "Summarizer",
            "model_id": self.model_id,
            "status": "ready"
        }

