import json,re,os,datetime
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

class TextMerger:
    """文本合并器：将语音识别的短句合并为完整段落"""
    def __init__(self,model_id:str):
        self.client=OpenAI(base_url="https://openrouter.ai/api/v1",api_key=os.environ.get("ARK_API_KEY"))
        self.model_id=model_id
        if not os.environ.get("ARK_API_KEY"):raise ValueError("需要ARK_API_KEY环境变量")
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
        prompt=f"""合并语义相关句子，保持顺序，返回JSON格式：
[{{"text":"合并文本","original_indices":[索引列表]}}]

输入：
{input_text}"""

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

if __name__=="__main__":
    merger=TextMerger("openrouter/horizon-beta")
    if merger.process_file("result_sentences.json","merged_result.json"):
        print("处理完成")
    else:print("处理失败")