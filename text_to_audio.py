from nanovllm_voxcpm import VoxCPM
import numpy as np
import soundfile as sf
from tqdm.asyncio import tqdm
import time
from nanovllm_voxcpm.models.voxcpm.server import AsyncVoxCPMServerPool
import torch
import os
# 在推理前设置显存分配策略
torch.cuda.empty_cache()
torch.cuda.set_per_process_memory_fraction(0.9)  # 预留10%显存给系统

# 使用更高效的显存分配器
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:128'


def merge_wav_files_without_resampling(file_list, output_file, target_sr):
    """
    合并多个WAV文件，但不重新采样

    Args:
        file_list: WAV文件路径列表
        output_file: 输出文件路径
        target_sr: 输出文件的目标采样率

    Note:
        此函数假设所有输入文件的采样率已经是target_sr
        如果不一致，会跳过该文件并给出警告
    """
    audio_segments = []
    skipped_files = []

    for i, wav_file in enumerate(file_list):
        print(f"处理文件 {i + 1}/{len(file_list)}: {os.path.basename(wav_file)}")

        # 读取WAV文件
        audio, sr = sf.read(wav_file)

        # 检查采样率
        if sr != target_sr:
            print(f"  ⚠️ 警告: 采样率不匹配 (文件: {sr}Hz, 目标: {target_sr}Hz) - 跳过此文件")
            skipped_files.append((wav_file, sr))
            continue

        # 如果是立体声，转换为单声道
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
            print(f"  - 立体声转换为单声道")

        audio_segments.append(audio)
        print(f"  ✓ 已添加，长度: {len(audio)} 样本")

    if not audio_segments:
        print("错误：没有有效的音频文件可以合并")
        return None, None

    # 合并所有音频段
    print(f"\n正在合并 {len(audio_segments)} 个音频段...")
    merged_audio = np.concatenate(audio_segments)

    # 计算总时长
    total_duration = len(merged_audio) / target_sr
    print(f"合并完成！总时长: {total_duration:.2f}秒")

    # 保存合并后的文件
    sf.write(output_file, merged_audio, target_sr)
    print(f"文件已保存: {output_file}")

    if skipped_files:
        print(f"\n跳过的文件 ({len(skipped_files)}个):")
        for f, sr in skipped_files:
            print(f"  - {os.path.basename(f)} (采样率: {sr}Hz)")

    return merged_audio, target_sr
'''
读取test.txt小说内容，去掉多余空行，转换成带序号的数组
'''
def readTestTxtToArray():
    with open("test.txt","r",encoding="utf-8") as file:
        textStr = file.read()
    text_array = textStr.split("\n")
    new_text_array = []
    for text in text_array:
        if text != "":
            new_text_array.append(text)
    return new_text_array

async def run_text_to_audio():
    """
    读取一章的内容，通过换行分割成文本数组，然后一句一句生成wav语音文件
    """
    text_array = readTestTxtToArray()
    print("Loading...")
    server: AsyncVoxCPMServerPool = VoxCPM.from_pretrained(
        "../VoxCPM1.5/",
        max_num_batched_tokens=8192,
        max_num_seqs=16,
        max_model_len=4096,
        gpu_memory_utilization=0.95,
        enforce_eager=False,
        devices=[0]
    )
    await server.wait_for_ready()
    # 准备参数
    wav_file = "./mp10s.wav"
    text = "苏宇说的淡然，“其他课程我都不用上了，执教老师答应过的，我不去没关系，你不去……你准备这时候被请家长？”"
    # 1. 读取WAV文件
    with open(wav_file, "rb") as f:
        wav_bytes = f.read()

    # 2. 添加到提示池，直接获得prompt_id
    prompt_id = await server.add_prompt(
        wav=wav_bytes,
        wav_format="wav",  # 指定格式
        prompt_text=text
    )
    print("Ready")
    model_info = await server.get_model_info()
    sample_rate = int(model_info["sample_rate"])
    wav_file_path_list = []
    use_sum = 0
    audio_duration = 0
    text_len = 0
    for i in range(0, len(text_array)):
        buf = []
        start_time = time.time()
        async for data in tqdm(
                server.generate(
                    target_text=text_array[i],
                    cfg_value=2,
                    prompt_id=prompt_id,
                )
        ):
            buf.append(data)
        wav = np.concatenate(buf, axis=0)
        end_time = time.time()

        time_used = end_time - start_time
        wav_duration = wav.shape[0] / sample_rate
        save_wav_file_path = "test-"+str(i)+".wav"
        wav_file_path_list.append(save_wav_file_path)
        print(save_wav_file_path+"：生成时间===========================")
        print(f"Sample rate: {sample_rate}")
        sf.write(save_wav_file_path, wav, sample_rate)
        print(f"Time: {end_time - start_time}s")
        print(f"RTF: {time_used / wav_duration}")
        print(save_wav_file_path+"：生成结束===========================")
        print()
        use_sum += time_used
        audio_duration += wav_duration
        text_len += len(text_array[i])
    await server.stop()
    print("生成一章总用时："+str(use_sum))
    print("一章的声音时长："+str(audio_duration))
    print("小说字符数："+str(text_len))

    merge_wav_files_without_resampling(
        wav_file_path_list,
        "一章.wav",
        target_sr=sample_rate
    )

async def main():
    print("Loading...")
    server: AsyncVoxCPMServerPool = VoxCPM.from_pretrained(
        "./VoxCPM1.5/",
        max_num_batched_tokens=8192,
        max_num_seqs=16,
        max_model_len=4096,
        gpu_memory_utilization=0.95,
        enforce_eager=False,
        devices=[0]
    )
    await server.wait_for_ready()
    # 准备参数
    wav_file = "./mp10s.wav"
    text = "苏宇说的淡然，“其他课程我都不用上了，执教老师答应过的，我不去没关系，你不去……你准备这时候被请家长？”"
    # 1. 读取WAV文件
    with open(wav_file, "rb") as f:
        wav_bytes = f.read()

    # 2. 添加到提示池，直接获得prompt_id
    prompt_id = await server.add_prompt(
        wav=wav_bytes,
        wav_format="wav",  # 指定格式
        prompt_text=text
    )
    print("Ready")
    model_info = await server.get_model_info()
    sample_rate = int(model_info["sample_rate"])

    buf = []
    start_time = time.time()
    async for data in tqdm(
            server.generate(
                target_text="有这么一个人呐，一个字都不认识，连他自己的名字都不会写，他上京赶考去了。哎，到那儿还就中了，不但中了，而且升来升去呀，还入阁拜相，你说这不是瞎说吗？哪有这个事啊。当然现在是没有这个事，现在你不能替人民办事",
                cfg_value=2,
                prompt_id=prompt_id,
            )
    ):
        buf.append(data)
    wav = np.concatenate(buf, axis=0)
    end_time = time.time()

    time_used = end_time - start_time
    wav_duration = wav.shape[0] / sample_rate
    print(f"Sample rate: {sample_rate}")
    sf.write("test.wav", wav, sample_rate)

    print(f"Time: {end_time - start_time}s")
    print(f"RTF: {time_used / wav_duration}")

    await server.stop()


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_text_to_audio())
