import json
import re
import os
import datetime
from typing import List, Dict, Any
from openai import OpenAI

class TextMerger:
    def __init__(self, model_id: str):
        """
        初始化文本合并器，使用OpenAI风格客户端
        
        :param model_id: 模型ID
        """
        # 初始化OpenAI客户端
        self.client = OpenAI(
            base_url="https://ark.cn-beijing.volces.com/api/v3",
            api_key=os.environ.get("ARK_API_KEY")
        )
        
        self.model_id = model_id
        
        if not os.environ.get("ARK_API_KEY"):
            raise ValueError("API密钥未提供，请设置ARK_API_KEY环境变量")
            
        if not self.model_id:
            raise ValueError("请提供模型ID(model_id)")

    def load_json(self, file_path: str) -> List[Dict[str, Any]]:
        """加载JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 检查加载的数据格式
                if isinstance(data, dict):
                    return data.get("result_sentences", [])
                elif isinstance(data, list):
                    return data
                else:
                    print(f"警告: JSON文件 '{file_path}' 的内容格式未知。")
                    return []
        except FileNotFoundError:
            print(f"错误: 文件 '{file_path}' 未找到。")
            return []
        except json.JSONDecodeError:
            print(f"错误: 文件 '{file_path}' 不是有效的JSON格式。")
            return []

    def save_json(self, data: List[Dict[str, Any]], file_path: str):
        """将数据保存到JSON文件"""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({"merged_sentences": data}, f, ensure_ascii=False, indent=4)

    def _format_time(self, ms: int) -> str:
        """将毫秒转换为 HH:MM:SS.ms 格式的字符串"""
        if not isinstance(ms, int):
            return str(ms)
        td = datetime.timedelta(milliseconds=ms)
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        milliseconds = td.microseconds // 1000
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

    def _merge_texts(self, sentences: list) -> list:
        """
        使用LLM合并文本的核心逻辑
        """
        if not sentences:
            return []

        # 准备给LLM的输入文本
        input_text = ""
        for i, s in enumerate(sentences):
            input_text += f"[{i}]: {s['text']}\n"

        # 构建prompt
        prompt = f"""
        你是一个专业的文本处理助手。你的任务是根据语义和上下文，将以下句子列表合并成更流畅、更完整的段落。
        请遵循以下规则：
        1. 只合并语义上紧密相连的句子。
        2. 不要改变句子的原始顺序。
        3. 以JSON格式返回结果，格式为一个包含多个对象的列表。
        4. 每个对象代表一个合并后的句子（或未合并的单个句子），并包含两个键：
            - "text": 合并后的文本内容。
            - "original_indices": 一个包含原始句子索引的列表。

        例如，如果句子[0]和[1]合并，句子[2]自成一句，句子[3]、[4]、[5]合并，你应该返回：
        [
            {{"text": "合并后的句子0和1", "original_indices": [0, 1]}},
            {{"text": "原始句子2", "original_indices": [2]}},
            {{"text": "合并后的句子3、4和5", "original_indices": [3, 4, 5]}}
        ]

        现在，请处理以下句子：
        {input_text}
        """

        try:
            # OpenAI风格API调用
            completion = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {"role": "system", "content": "你是一个专业的文本处理助手。"},
                    {"role": "user", "content": prompt},
                ],
                stream=False
            )
            
            llm_response_content = completion.choices[0].message.content
            
            # 提取JSON部分
            json_match = re.search(r'```json\n(.*?)```', llm_response_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = llm_response_content

            merged_groups = json.loads(json_str)
            
            # 重建结果
            final_results = []
            for group in merged_groups:
                indices = group['original_indices']
                if not indices:
                    continue
                
                merged_text = " ".join(sentences[i]['text'] for i in indices)
                start_time = sentences[indices[0]]['start_time']
                end_time = sentences[indices[-1]]['end_time']
                
                final_results.append({
                    "text": merged_text,
                    "start_time": start_time,
                    "end_time": end_time
                })

            # 格式化时间
            for result in final_results:
                result['start_time'] = self._format_time(result['start_time'])
                result['end_time'] = self._format_time(result['end_time'])
                
            return final_results

        except Exception as e:
            print(f"调用LLM或解析其响应时出错: {e}")
            # 出错时返回原始句子（格式化时间）
            for s in sentences:
                s['start_time'] = self._format_time(s['start_time'])
                s['end_time'] = self._format_time(s['end_time'])
            return sentences


    def process_file(self, input_file: str, output_file: str) -> bool:
        """处理单个文件：加载、合并、保存"""
        sentences = self.load_json(input_file)
        if not sentences:
            print("输入文件中没有找到句子或加载失败。")
            return False
        
        merged_data = self._merge_texts(sentences)
        
        if merged_data:
            self.save_json(merged_data, output_file)
            return True
        else:
            print("合并过程没有产生任何结果。")
            return False

if __name__ == "__main__":
    try:
        input_file = "result_sentences.json"
        output_file = "merged_result.json"
        
        # 使用OpenAI风格客户端，指定模型ID
        merger = TextMerger(
            model_id="kimi-k2-250711"  # 与OpenAI调用示例中的模型一致
        )
        
        if not os.path.exists(input_file):
            print(f"错误：输入文件 '{input_file}' 不存在于当前目录")
            exit(1)
        
        print(f"正在处理文件: {input_file}...")
        success = merger.process_file(input_file, output_file)
        
        if success:
            print(f"处理完成，结果已保存到 {output_file}")
        else:
            print("处理失败")
            
    except ValueError as e:
        print(f"初始化失败: {e}")
        exit(1)
    except Exception as e:
        print(f"运行出错: {e}")
        exit(1)