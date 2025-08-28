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
Translate the input subtitle sentences into several phases based on semantic relevance. Each phase shall have consistent themes and closely connected contexts, with the following requirements:
Maintain the original order without disruption.
Do not merge all sentences into a single whole; the number of phases shall be 2 or more.
If two sentences have significantly different themes, they shall be grouped into different phases.
Output a JSON array, where each element contains:
"text": The merged complete text (sentences connected by spaces)
"original_indices": A list of original sentence indices involved in the merge (in the original order)
Input:
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

