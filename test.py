import json


def createWavByText():
    import torch
    import soundfile as sf
    from qwen_tts import Qwen3TTSModel
    model = Qwen3TTSModel.from_pretrained(
        "./Qwen3-TTS-12Hz-0.6B-CustomVoice/",
        device_map="cuda:0",
        dtype=torch.bfloat16,
        attn_implementation="flash_attention_2",
    )

    # single inference
    wavs, sr = model.generate_custom_voice(
        text="""
       少年的身躯微微一颤，浑身血液倒流，隐隐灵气光华汇聚，钻入躯体。
        """,
        language="Chinese",
        # Pass `Auto` (or omit) for auto language adaptive; if the target language is known, set it explicitly.
        speaker="Ono_Anna",
        instruct="用平稳的语气说出来",  # Omit if not needed.
    )
    sf.write("output_custom_voice.wav", wavs[0], sr)
    # batch inference
    # wavs, sr = model.generate_custom_voice(
    #     text=[
    #         "其实我真的有发现，我是一个特别善于观察别人情绪的人。",
    #         "She said she would be here by noon."
    #     ],
    #     language=["Chinese", "English"],
    #     speaker=["Vivian", "Ryan"],
    #     instruct=["", "Very happy."]
    # )
    # sf.write("output_custom_voice_1.wav", wavs[0], sr)
    # sf.write("output_custom_voice_2.wav", wavs[1], sr)

def strLen():
    str1 = """
    11111
    22222
    """
    new_str1 = str1.replace(" ","").replace("\n","")
    print(len(new_str1))
    print(new_str1[0:5])
    print(new_str1[5:10])

def checkQwenOutputOnJson():
    with open("test.json","r",encoding="utf-8") as file:
        outputObj = json.load(file)
    return outputObj


def count_chinese_chars(text):
    count = 0
    # 遍历字符串中的每个字符
    for char in text:
        # 判断字符是否为汉字（Unicode编码范围：0x4E00 至 0x9FFF）
        if '\u4e00' <= char <= '\u9fff':
            count += 1
    return count
if __name__ == '__main__':
    result_json = checkQwenOutputOnJson()
    sentenceList = result_json["sentenceList"]
    text = ""
    for sentence in sentenceList:
        text += sentence["context"]
    text_count = count_chinese_chars(text)
    with open("test.txt","r",encoding="utf-8") as file:
        new_text = file.read()
    new_text_count = count_chinese_chars(new_text)
    print("json文本数量："+str(text_count))
    print("txt文本数量："+str(new_text_count))