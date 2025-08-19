import json,re,os,datetime,asyncio
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

class TextMerger:
    """文本合并器：将语音识别的短句合并为完整段落"""
    def __init__(self,model_id:str):
        self.client=OpenAI(base_url=os.environ.get("OPENAI_BASE_URL"),api_key=os.environ.get("OPENAI_API_KEY"))
        self.model_id=model_id
        if not os.environ.get("OPENAI_API_KEY"):raise ValueError("需要OPENAI_API_KEY环境变量")
        if not model_id:raise ValueError("需要model_id")

    def load_json(self,fp:str)->list:
        try:
            with open(fp,'r',encoding='utf-8') as f:
                d=json.load(f)
                return d.get("result_sentences",[]) if isinstance(d,dict) else d if isinstance(d,list) else []
        except:return []

    def save_json(self,data:list,fp:str):
        with open(fp,'w',encoding='utf-8') as f:json.dump({"merged_sentences":data},f,ensure_ascii=False,indent=4)

    def _format_time(self,ms:int)->str:
        if not isinstance(ms,int):return str(ms)
        td=datetime.timedelta(milliseconds=ms)
        h,r=divmod(td.seconds,3600)
        m,s=divmod(r,60)
        return f"{h:02d}:{m:02d}:{s:02d}.{td.microseconds//1000:03d}"

    def _merge_texts(self,sentences:list)->list:
        if not sentences:return []

        input_text="\n".join([f"[{i}]: {s['text']}" for i,s in enumerate(sentences)])
        prompt = f"""
将输入的字幕句子按语义相关性合并成几个阶段，每个阶段的内容应主题一致、上下文紧密相关。
注意：
1. 保持原有顺序，不能打乱。
2. 不要把所有句子合并成一个整体，阶段数量应为 2 个及以上。
3. 如果两个句子主题差异较大，则应分到不同阶段。
4. 输出 JSON 数组，每个元素包含：
   - "text": 合并后的完整文本（句子之间用空格连接）
   - "original_indices": 参与合并的原句索引列表（按原顺序）

输入：
{input_text}
"""

        try:
            resp=self.client.chat.completions.create(model=self.model_id,messages=[{"role":"user","content":prompt}])
            content=resp.choices[0].message.content

            json_match=re.search(r'```json\n(.*?)```',content,re.DOTALL)
            json_str=json_match.group(1) if json_match else content
            groups=json.loads(json_str)

            results=[]
            for g in groups:
                idx=g['original_indices']
                if idx:
                    results.append({
                        "text":" ".join(sentences[i]['text'] for i in idx),
                        "start_time":self._format_time(sentences[idx[0]]['start_time']),
                        "end_time":self._format_time(sentences[idx[-1]]['end_time'])
                    })
            return results
        except Exception as e:
            print(f"LLM错误: {e}")
            for s in sentences:
                s['start_time']=self._format_time(s['start_time'])
                s['end_time']=self._format_time(s['end_time'])
            return sentences


    def process_file(self,input_file:str,output_file:str)->bool:
        sentences=self.load_json(input_file)
        if not sentences:return False
        merged=self._merge_texts(sentences)
        if merged:
            self.save_json(merged,output_file)
            return True
        return False

    async def process_file_async(self, input_file: str, output_file: str) -> bool:
        """异步处理文件"""
        try:
            # 在线程池中执行同步方法
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self.process_file,
                input_file,
                output_file
            )
            return result
        except Exception as e:
            raise RuntimeError(f"文本合并失败: {e}")

    def get_service_status(self) -> dict:
        """获取服务状态"""
        return {
            "service": "TextMerger",
            "model_id": self.model_id,
            "status": "ready"
        }

