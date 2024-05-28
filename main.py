from fastapi import FastAPI, HTTPException, Query
import os
import asyncio
import edge_tts
from typing import Union
from pydantic import BaseModel

app = FastAPI()

# Define default constants for TTS
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
DEFAULT_OUTPUT_DIR = "/"

@app.get("/")
def read_root():
    return "Hello, World!"

class TTSRequest(BaseModel):
    text: str
    voice: str = DEFAULT_VOICE
    output_dir: str = DEFAULT_OUTPUT_DIR

@app.post("/generate-tts")
async def generate_tts(request_data: TTSRequest):
    text = request_data.text
    voice = request_data.voice
    output_dir = request_data.output_dir

    """Endpoint to generate TTS and subtitles"""
    try:
        output_file = os.path.join(output_dir, "output.mp3")
        webvtt_file = os.path.join(output_dir, "output.srt")
        # 确保路径中的目录都已创建
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        await amain(text, voice, output_file, webvtt_file)
        return {"message": "成功生成TTS和字幕", "audio_file": output_file, "subtitle_file": webvtt_file}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 生成语音和字幕
async def amain(text: str, voice: str, output_file: str, webvtt_file: str) -> None:
    """Main function to perform TTS and generate subtitles"""
    communicate = edge_tts.Communicate(text, voice)
    submaker = edge_tts.SubMaker()
    with open(output_file, "wb") as file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.create_sub((chunk["offset"], chunk["duration"]), chunk["text"])

    # with open(webvtt_file, "w", encoding="utf-8") as file:
    #     word = submaker.generate_subs()
    #     if word not in ["WEBVTT", "WEBVTT\n", "\n"]:
    #         file.write(word)
    subs = submaker.generate_subs()
    if subs.strip():
        srt_content = generate_srt(subs)
        with open(webvtt_file, "w", encoding="utf-8") as file:
            file.write(srt_content)

# 解析str字幕块
def generate_srt(subs: str) -> str:
    # 将 "WEBVTT" 替换为空字符串
    subs = subs.replace("WEBVTT", "")
    lines = subs.strip().split("\r\n")
    srt_subs = ""
    count = 1
    timestamp = None
    text = ""
    for line in lines:
        if not line.strip():  # 如果是空行，表示一个字幕块的结束
            if timestamp and text:  # 确保时间戳和文本都存在
                start, end = timestamp.split(" --> ")
                srt_subs += f"{count}\n{start} --> {end}\n{text}\n\n"
                count += 1
                timestamp = None
                text = ""
        elif " --> " in line:  # 如果包含时间戳信息
            timestamp = line
        else:  # 否则是文本行
            text += line + " "
    # 添加最后一个字幕块
    if timestamp and text:
        start, end = timestamp.split(" --> ")
        srt_subs += f"{count}\n{start} --> {end}\n{text.strip()}\n\n"
    return srt_subs.strip()





if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
