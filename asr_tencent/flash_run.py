# -*- coding: utf-8 -*-

import time
import sys
import threading
from datetime import datetime
import json
sys.path.append("../..")
from common import credential
from asr import flash_recognizer

# 注意：使用前务必先填写APPID、SECRET_ID、SECRET_KEY，否则会无法运行！！！
APPID = "1359872096"
SECRET_ID = "AKIDd9UdYGlGYdU8YkiTinfJvKl7IclgQxGM"
SECRET_KEY = "ub4JLGAvojYO3VkofI7nJcT7ZoqhLrCJ"
ENGINE_TYPE = "16k_zh"

if __name__=="__main__":
    if APPID == "":
        print("Please set APPID!")
        exit(0)
    if SECRET_ID == "":
        print("Please set SECRET_ID!")
        exit(0)
    if SECRET_KEY == "":
        print("Please set SECRET_KEY!")
        exit(0)

    credential_var = credential.Credential(SECRET_ID, SECRET_KEY)
    # 新建FlashRecognizer，一个recognizer可以执行N次识别请求
    recognizer = flash_recognizer.FlashRecognizer(APPID, credential_var)

    # 新建识别请求
    req = flash_recognizer.FlashRecognitionRequest(ENGINE_TYPE)
    req.set_filter_modal(0)
    req.set_filter_punc(0)
    req.set_filter_dirty(0)
    req.set_voice_format("wav")
    req.set_word_info(2)
    req.set_convert_num_mode(1)

    # 音频路径
    audio = "./test.wav"
    with open(audio, 'rb') as f:
        #读取音频数据
        data = f.read()
        #执行识别
        resultData = recognizer.recognize(req, data)
        resp = json.loads(resultData)
        request_id = resp["request_id"]
        code = resp["code"]
        if code != 0:
            print("recognize faild! request_id: ", request_id, " code: ", code, ", message: ", resp["message"])
            exit(0)

        print("request_id: ", request_id)
        # 收集每个句子的text、start_time和end_time
        sentences = []
        for channl_result in resp["flash_result"]:
            for sentence in channl_result.get("sentence_list", []):
                sentences.append({
                    "text": sentence["text"],
                    "start_time": sentence["start_time"],
                    "end_time": sentence["end_time"]
                })
        # 保存为json文件
        with open("result_sentences.json", "w", encoding="utf-8") as jf:
            json.dump(sentences, jf, ensure_ascii=False, indent=4)
        print("已保存句子信息到 result_sentences.json")
