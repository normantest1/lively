import re
import threading
import os
from pathlib import Path
from struct import pack_into

import torch
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
from tqdm.asyncio import tqdm
import numpy as np
import soundfile as sf

from bean.beans import RoleAudio, Role
from utils.config import load_config
from logger import log, log_error
config_path = Path(__file__).resolve().parent / "config/lively_config.json"
ROOT_DIR = Path(__file__).resolve().parent

import json
import os
import anthropic

from bean.beans import Novel, NovelName, get_db, Role

import concurrent.futures
from typing import List, Dict, Optional, Callable
import asyncio
import time
import traceback
import queue
remove_silence_lock = threading.Lock()

def remove_silence_from_audio(
    input_path: str,
    output_path: str,
    silence_thresh: int = -40,
    min_silence_len: int = 3000,
    keep_short_silence: int = 500
) -> dict:
    """
    删除音频中的长静音部分，保留短停顿
    
    支持多线程并发调用，每个调用使用独立的资源

    参数:
        input_path (str): 输入音频文件路径（支持 .wav, .mp3, .ogg, .flac, .m4a 等格式）
        output_path (str): 输出音频文件路径
        silence_thresh (int): 静音阈值，单位为dBFS，默认为-40（低于此值的被认为是静音）
        min_silence_len (int): 最小静音持续时间，单位为毫秒，默认为3000ms（3秒）
                            只有超过此值的静音才会被删除
        keep_short_silence (int): 保留的短静音长度，单位为毫秒，默认为500ms
                                长静音会被压缩到此长度

    返回:
        dict: 包含处理信息的字典
            - success (bool): 处理是否成功
            - original_duration (float): 原始音频时长（秒）
            - processed_duration (float): 处理后音频时长（秒）
            - removed_duration (float): 删除的静音总时长（秒）
            - removed_count (int): 删除的静音段数量
            - message (str): 处理信息或错误信息
    """
    with remove_silence_lock:
        try:
            # 检查输入文件是否存在
            if not os.path.exists(input_path):
                return {
                    "success": False,
                    "original_duration": 0,
                    "processed_duration": 0,
                    "removed_duration": 0,
                    "removed_count": 0,
                    "message": f"输入文件不存在: {input_path}"
                }

            # 获取文件扩展名
            file_ext = os.path.splitext(input_path)[1].lower()

            # 加载音频
            audio = AudioSegment.from_file(input_path)

            # 记录原始时长
            original_duration = len(audio) / 1000.0

            # 检测非静音部分
            nonsilent_ranges = detect_nonsilent(
                audio,
                min_silence_len=100,  # 使用较小的值检测所有可能的静音
                silence_thresh=silence_thresh
            )

            # 如果没有检测到非静音部分，直接返回原始音频
            if not nonsilent_ranges:
                audio.export(output_path, format=file_ext[1:] if file_ext else 'wav')
                return {
                    "success": True,
                    "original_duration": original_duration,
                    "processed_duration": original_duration,
                    "removed_duration": 0,
                    "removed_count": 0,
                    "message": "未检测到非静音部分，保持原始音频"
                }

            # 构建处理后的音频
            processed_audio = AudioSegment.empty()
            removed_count = 0
            total_removed_duration = 0

            for i, (start_ms, end_ms) in enumerate(nonsilent_ranges):
                # 添加当前非静音片段
                chunk = audio[start_ms:end_ms]
                processed_audio += chunk

                # 计算下一个非静音片段之前的静音长度
                if i < len(nonsilent_ranges) - 1:
                    next_start_ms = nonsilent_ranges[i + 1][0]
                    silence_duration = next_start_ms - end_ms

                    # 判断是否为长静音
                    if silence_duration >= min_silence_len:
                        # 长静音：压缩到保留的短静音长度
                        if keep_short_silence > 0:
                            silence = AudioSegment.silent(duration=keep_short_silence)
                            processed_audio += silence
                            removed_duration = (silence_duration - keep_short_silence) / 1000.0
                        else:
                            removed_duration = silence_duration / 1000.0

                        total_removed_duration += removed_duration
                        removed_count += 1
                    else:
                        # 短静音：保留原样
                        silence = AudioSegment.silent(duration=silence_duration)
                        processed_audio += silence

            # 确保输出目录存在
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            # 导出处理后的音频
            export_format = file_ext[1:] if file_ext else 'wav'
            processed_audio.export(output_path, format=export_format)

            # 计算统计信息
            processed_duration = len(processed_audio) / 1000.0

            return {
                "success": True,
                "original_duration": original_duration,
                "processed_duration": processed_duration,
                "removed_duration": total_removed_duration,
                "removed_count": removed_count,
                "message": f"成功处理，删除了 {removed_count} 处长静音（共 {total_removed_duration:.2f} 秒），保留了短停顿"
            }

        except Exception as e:
            log_error(f"remove_silence_from_audio 处理音频时出错 (input_path={input_path}, output_path={output_path}): {str(e)}")
            traceback.print_exc()
            return {
                "success": False,
                "original_duration": 0,
                "processed_duration": 0,
                "removed_duration": 0,
                "removed_count": 0,
                "message": f"处理音频时出错: {str(e)}"
            }


def batch_remove_silence(
    input_dir: str,
    output_dir: str,
    silence_thresh: int = -40,
    min_silence_len: int = 3000,
    keep_short_silence: int = 500,
    file_pattern: str = "*.wav"
) -> list:
    """
    批量处理目录中的音频文件，删除长静音部分，保留短停顿

    参数:
        input_dir (str): 输入目录路径
        output_dir (str): 输出目录路径
        silence_thresh (int): 静音阈值（dBFS）
        min_silence_len (int): 最小静音持续时间（毫秒），超过此值的静音会被处理
        keep_short_silence (int): 保留的短静音长度（毫秒）
        file_pattern (str): 文件匹配模式，如 "*.wav", "*.mp3", "*.wav"

    返回:
        list: 每个文件的处理结果列表
    """
    import glob

    # 确保输出目录存在
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # 获取所有匹配的文件
    pattern = os.path.join(input_dir, file_pattern)
    files = glob.glob(pattern)

    results = []

    for input_file in files:
        filename = os.path.basename(input_file)
        output_file = os.path.join(output_dir, filename)

        print(f"正在处理: {filename}")
        log(f"正在处理: {filename}")
        result = remove_silence_from_audio(
            input_path=input_file,
            output_path=output_file,
            silence_thresh=silence_thresh,
            min_silence_len=min_silence_len,
            keep_short_silence=keep_short_silence
        )

        result["input_file"] = input_file
        result["output_file"] = output_file
        results.append(result)

        if result["success"]:
            print(f"  ✓ 成功: {result['message']}")
            log(f"  ✓ 成功: {result['message']}")
        else:
            print(f"  ✗ 失败: {result['message']}")
            log(f"  ✗ 失败: {result['message']}")

    return results



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
        log(f"处理文件 {i + 1}/{len(file_list)}: {os.path.basename(wav_file)}")

        # 读取WAV文件
        audio, sr = sf.read(wav_file)

        # 检查采样率
        if sr != target_sr:
            print(f"  ⚠️ 警告: 采样率不匹配 (文件: {sr}Hz, 目标: {target_sr}Hz) - 跳过此文件")
            log(f"  ⚠️ 警告: 采样率不匹配 (文件: {sr}Hz, 目标: {target_sr}Hz) - 跳过此文件")
            skipped_files.append((wav_file, sr))
            continue

        # 如果是立体声，转换为单声道
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
            print(f"  - 立体声转换为单声道")
            log(f"  - 立体声转换为单声道")

        audio_segments.append(audio)
        print(f"  ✓ 已添加，长度: {len(audio)} 样本")
        log(f"  ✓ 已添加，长度: {len(audio)} 样本")

    if not audio_segments:
        print("错误：没有有效的音频文件可以合并")
        log("错误：没有有效的音频文件可以合并")
        return None, None

    # 合并所有音频段
    print(f"\n正在合并 {len(audio_segments)} 个音频段...")
    log(f"\n正在合并 {len(audio_segments)} 个音频段...")
    merged_audio = np.concatenate(audio_segments)

    # 计算总时长
    total_duration = len(merged_audio) / target_sr
    print(f"合并完成！总时长: {total_duration:.2f}秒")
    log(f"合并完成！总时长: {total_duration:.2f}秒")

    # 保存合并后的文件
    sf.write(output_file, merged_audio, target_sr)
    print(f"文件已保存: {output_file}")
    log(f"文件已保存: {output_file}")

    if skipped_files:
        print(f"\n跳过的文件 ({len(skipped_files)}个):")
        log(f"\n跳过的文件 ({len(skipped_files)}个):")
        for f, sr in skipped_files:
            print(f"  - {os.path.basename(f)} (采样率: {sr}Hz)")
            log(f"  - {os.path.basename(f)} (采样率: {sr}Hz)")
    for file in file_list:
        os.remove(file)
    # result = remove_silence_from_audio(
    #     input_path=output_file,
    #     output_path=output_file,
    #     silence_thresh=-40,  # -40 dBFS
    #     min_silence_len=3000,  # 3秒以上的静音才处理
    #     keep_short_silence=500  # 短停顿保留500ms
    # )
    # print("\n静音处理结果:")
    # log("\n静音处理结果:")
    # print(f"  原始时长: {result['original_duration']:.2f} 秒")
    # log(f"  原始时长: {result['original_duration']:.2f} 秒")
    # print(f"  处理后时长: {result['processed_duration']:.2f} 秒")
    # log(f"  处理后时长: {result['processed_duration']:.2f} 秒")
    # print(f"  删除静音: {result['removed_duration']:.2f} 秒")
    # log(f"  删除静音: {result['removed_duration']:.2f} 秒")
    # print(f"  删除段数: {result['removed_count']}")
    # log(f"  删除段数: {result['removed_count']}")
    # print(f"  状态: {'成功' if result['success'] else '失败'}")
    # log(f"  状态: {'成功' if result['success'] else '失败'}")
    # print(f"  信息: {result['message']}")
    # log(f"  信息: {result['message']}")
    return merged_audio, target_sr
async def load_role_audio(novel_name,lux_tts):
    """
    新版
    加载所有音频角色到内存中，提高音频生成速度
    :param novel_name: 这个已经不需要了，但为了不修改其它代码，所以不删需要加载角色的小说名字
    :param server: nanollm_voxcpe的模型对象
    :return:
    """
    try:
        # 加载配置信息
        load_role_count = load_config(config_path,"preload_role_count")
        audio_role_list = RoleAudio.select().limit(load_role_count)
        load_role_list = []
        ref_duration = 1000
        rms = 0.01
        for audio_role in audio_role_list:
            prompt_id = lux_tts.encode_prompt(
                audio_role.audio_path,
                duration=ref_duration,
                rms=rms,
                prompt_text=audio_role.audio_text
            )
            tmep_role = {
                "audio_role_name": audio_role.role_name,
                "prompt_id": prompt_id
            }
            load_role_list.append(tmep_role)
        return load_role_list
    except Exception as e:
        log_error(f"load_role_audio 加载角色音频失败 (novel_name={novel_name}): {str(e)}")
        traceback.print_exc()
        return []
async def load_role_audio_old(novel_name,lux_tts):
    """
    旧版
    加载前x个主要角色到内存中，提高音频生成速度
    :param novel_name: 需要加载角色的小说名字
    :param server: nanollm_voxcpe的模型对象
    :return:
    """
    try:
        # 加载配置信息
        load_role_count = load_config(config_path,"preload_role_count")
        #查询当前解析的最大章节数
        role_chapter_max = Role.select().where(
            Role.novel_name == novel_name
        ).order_by(Role.create_time.asc()).first()
        #将常用的几个角色信息加载出来
        text_role_lsit = Role.select().order_by(
            -(
                Role.role_count / role_chapter_max.chapter_count
            )
        ).limit(load_role_count)
        audio_role_name_list = []
        for role in text_role_lsit:
            if role.bind_audio_name != "":
                audio_role_name_list.append(role.bind_audio_name)
        audio_role_list = RoleAudio.select().where(RoleAudio.role_name.in_(audio_role_name_list))
        load_role_list = []
        ref_duration = 1000
        rms = 0.01
        for audio_role in audio_role_list:
            # with open(audio_role.audio_path, "rb") as f:
            #     wav_bytes = f.read()

            prompt_id = lux_tts.encode_prompt(
                audio_role.audio_path,
                duration=ref_duration,
                rms=rms,
                prompt_text=audio_role.audio_text
            )
            # prompt_id = await server.add_prompt(
            #     wav=wav_bytes,
            #     wav_format="wav",  # 指定格式
            #     prompt_text=audio_role.audio_text
            # )
            tmep_role = {
                "audio_role_name": audio_role.role_name,
                "prompt_id": prompt_id
            }
            load_role_list.append(tmep_role)
        return load_role_list
    except Exception as e:
        log_error(f"load_role_audio 加载角色音频失败 (novel_name={novel_name}): {str(e)}")
        traceback.print_exc()
        return []

def get_folders(path):
    """
    根据传入的路径，生成路径下的文件夹列表
    :param path: 路径
    :return:
    """
    folders = [entry.name for entry in os.scandir(path) if entry.is_dir()]
    return folders

def update_audio_role():
    """
    加载./audios文件夹下的角色音频信息到数据库
    :return:
    """
    try:
        folder_path = './audios'
        role_name_list = get_folders(folder_path)
        for role_name in role_name_list:
            with open(f"{folder_path}/{role_name}/gender.txt", "r",encoding="utf-8") as f:
                role_gender = f.read()
            with open(f"{folder_path}/{role_name}/text.txt", "r",encoding="utf-8") as f:
                audio_text = f.read()
            audio_path = ROOT_DIR / f"audios/{role_name}/audio.wav"
            audio_uri = f"{role_name}/audio.wav"
            old_role = RoleAudio.get_or_none(RoleAudio.role_name == role_name)
            # 如果角色不存在，则添加角色
            if old_role is None:
                RoleAudio.create(
                    role_name=role_name,
                    gender=role_gender,
                    audio_text=audio_text,
                    audio_path=audio_path,
                    citation_count = 0,
                    audio_uri=audio_uri
                )
    except Exception as e:
        log_error(f"update_audio_role 更新角色音频信息失败: {str(e)}")
        traceback.print_exc()
def extract_chinese(text):
    # 只保留中文字符
    res = re.findall(r'[\u4e00-\u9fff]', text)
    return ''.join(res)


def extract_dialogue_and_narration(text: str) -> list:
    """
    提取文本中的角色台词（「」、"" 内）和旁白（符号外），按原文顺序返回
    :param text: 输入的原始文本
    :return: 按顺序排列的台词+旁白列表
    """
    # 定义对话符号对：开始符号 → 结束符号
    quote_pairs = {
        '「': '」',
        '"': '"'
    }
    result = []
    start = 0
    n = len(text)

    while start < n:
        # 查找下一个对话开始符号的位置
        next_quote_pos = -1
        quote_char = None

        # 遍历所有对话开头符号，找到最近的一个
        for q_start in quote_pairs:
            pos = text.find(q_start, start)
            if pos != -1 and (next_quote_pos == -1 or pos < next_quote_pos):
                next_quote_pos = pos
                quote_char = q_start

        # 没有找到任何对话符号，剩余全部是旁白
        if next_quote_pos == -1:
            narration = text[start:].strip()
            if narration:
                result.append(narration)
            break

        # 提取对话符号之前的旁白
        narration = text[start:next_quote_pos].strip()
        if narration:
            result.append(narration)

        # 找到对应的结束符号
        end_quote = quote_pairs[quote_char]
        end_pos = text.find(end_quote, next_quote_pos + 1)

        # 没有匹配的结束符号，把剩下的全部当作台词
        if end_pos == -1:
            dialogue = text[next_quote_pos:].strip()
            if dialogue:
                result.append(dialogue)
            start = n
            continue

        # 提取完整对话
        dialogue = text[next_quote_pos:end_pos + 1].strip()
        if dialogue:
            result.append(dialogue)

        # 移动指针继续处理
        start = end_pos + 1

    return result

async def generate_chapter_audio(chapter_role_list,role_audio_id,novel_name,novel_id,lux_tts,cancel_event=None):
    """
    生成章节音频
    
    参数:
        chapter_role_list: 章节角色列表
        role_audio_id: 角色音频ID列表
        novel_name: 小说名
        novel_id: 小说ID
        server: TTS服务器
        cancel_event: 取消事件，用于支持任务取消（可选）
    """
    try:
        wav_file_path_list = []
        temp_path = ROOT_DIR / "temp"
        save_chapter_audio_path = ROOT_DIR / f"save/{novel_name}"
        if not os.path.exists(save_chapter_audio_path):
            os.mkdir(save_chapter_audio_path)
        if not os.path.exists(temp_path):
            os.mkdir(temp_path)

        # 🔍 诊断日志：检查 cancel_event 的状态
        log(f"🔍 [诊断] generate_chapter_audio 收到 cancel_event: {cancel_event is not None}, is_set: {cancel_event.is_set() if cancel_event else 'N/A'}")

        # 检查是否被取消
        if cancel_event and cancel_event.is_set():
            log(f"⚠️ 章节生成任务被取消 (novel_name={novel_name}, novel_id={novel_id}, 阶段：初始化)")
            return False

        # 获取对应小说的旁白的声音
        narration_role = Role.select().where(
            (Role.novel_name == novel_name)&
            (Role.role_name == "旁白")
        ).get_or_none()
        
        # 再次检查是否被取消
        if cancel_event and cancel_event.is_set():
            log(f"⚠️ 章节生成任务被取消 (novel_name={novel_name}, novel_id={novel_id}, 阶段：获取旁白)")
            return False
        
        log(f"🎬 开始生成章节音频: {novel_name}, {novel_id}, 共 {len(chapter_role_list)} 句")
        
        narration_role_audio = RoleAudio.select().where(
            RoleAudio.role_name == narration_role.bind_audio_name
        ).get_or_none()
        # 获取旁白音频文件
        ref_duration = 1000
        rms = 0.01
        narration_prompt_id = lux_tts.encode_prompt(
            narration_role_audio.audio_path,
            duration=ref_duration,
            rms=rms,
            prompt_text=extract_chinese(narration_role_audio.audio_text)
        )
        # with open(narration_role_audio.audio_path, "rb") as f:
        #     narration_wav_bytes = f.read()
        # narration_prompt_id = await server.add_prompt(
        #     wav=narration_wav_bytes,
        #     wav_format="wav",  # 指定格式
        #     prompt_text=narration_role_audio.audio_text
        # )
        # log(f"给 {novel_name} 的 {narration_role.role_name} 分配 {narration_role_audio.role_name}")
        # print(f"给 {novel_name} 的 {narration_role.role_name} 分配 {narration_role_audio.role_name}")
        # model_info = await server.get_model_info()
        # sample_rate = int(model_info["sample_rate"])
        chapter_name = "-".join(chapter_role_list[0].get('text').strip().split())

        save_chapter_file_path = save_chapter_audio_path / f"{novel_id}-{chapter_name}.wav"

        generate_chapter_audio_duration = 0
        generate_chapter_audio_time = 0
        t_shift = 0.9
        # 从配置文件加载生成步数和语音速度
        num_steps = load_config(config_path, "inference_steps") or 6
        speed = load_config(config_path, "speech_speed") or 0.9
        sample_rate = 48000
        return_smooth = False
        for (index,chapter_role) in enumerate(chapter_role_list):
            # 每次循环都检查是否被取消
            if cancel_event and cancel_event.is_set():
                log(f"⚠️ 章节生成任务在第 {index+1}/{len(chapter_role_list)} 句前被取消 (novel_name={novel_name}, novel_id={novel_id})")
                # 清理已生成的临时文件
                for temp_file in wav_file_path_list:
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    except:
                        pass
                return False
            
            # log(f"🎬 [{novel_name}] 开始生成第 {index+1}/{len(chapter_role_list)} 句")
            
            # print(chapter_role_list)
            # break
            start_time = time.time()
            wav_duration = 0
            role_prompt_id = ""
            temp_save_wav_file_path = temp_path / f"{chapter_name}-{index}.wav"
            chapter_text = chapter_role.get("text").replace("…","").replace("·","").replace("(","").replace(")","").replace("[","").replace("]","").replace("{","").replace("}","").replace("<","").replace(">","").replace("-","").replace("_","").replace("@","").replace("#","").replace("*","").replace("\\","").replace("|","").replace("~","").replace("`","").replace(".","").replace("　","").replace("　","").replace("—","")
            if chapter_text == "":
                continue
            buf = []
            print(f"小说文本：{chapter_text}")
            log(f"小说文本：{chapter_text}")
            #生成旁白声音
            if chapter_role.get("type") == "narration":
                chapter_text = chapter_text.replace("「", "").replace("」", "").replace("”", "").replace("”", "").replace("？", "").replace("?","").replace("!", "").replace("！", "")
                if chapter_text == "":
                    continue
                wav = lux_tts.generate_speech(chapter_text, narration_prompt_id, num_steps=num_steps, t_shift=t_shift,
                                                    speed=speed, return_smooth=return_smooth)
                wav = wav.numpy().squeeze()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                # async for data in tqdm(
                #         server.generate(
                #             target_text=chapter_text,
                #             cfg_value=2,
                #             prompt_id=narration_prompt_id,
                #         )
                # ):
                #     buf.append(data)
                # wav = np.concatenate(buf, axis=0)
                sf.write(temp_save_wav_file_path, wav, sample_rate)
                wav_file_path_list.append(temp_save_wav_file_path)
                wav_duration = len(wav) / sample_rate
                generate_chapter_audio_duration += wav_duration
            #生成角色声音
            elif chapter_role.get("type") == "role":
                role_name = chapter_role.get("role_name")
                role_prompt_id = ""
                for prompt_id in role_audio_id:
                    #如果生成的角色声音在预加载的角色声音列表里面，则加载角色音频id
                    if role_name == prompt_id.get("audio_role_name"):
                        role_prompt_id = prompt_id.get("prompt_id")
                        break
                    #如果不存在角色预加载音频里面，则从根据角色名数据库预加载
                    """
                    这里假设传入的chapter_role_list列表是[{
                    "role_name": "张三",
                    "type": "narration或role",
                    "bind_role_audio_name": "素琴",
                    "text":"小说内容"
                    }]
                    """
                if role_prompt_id == "":
                    role_audio_data = RoleAudio.get(role_name=chapter_role.get("bind_role_audio_name"))
                    role_prompt_id = lux_tts.encode_prompt(role_audio_data.audio_path, duration=ref_duration, rms=rms,
                                                           prompt_text=extract_chinese(role_audio_data.audio_text))

                    # with open(role_audio_data.audio_path, "rb") as f:
                    #     role_wav_bytes = f.read()
                    # role_prompt_id = await server.add_prompt(
                    #     wav=role_wav_bytes,
                    #     wav_format="wav",  # 指定格式
                    #     prompt_text=role_audio_data.audio_text
                    # )
                result_list = extract_dialogue_and_narration(chapter_text)
                for result_index,result_text in enumerate(result_list):
                    print(f"分割的文本：{result_text}")
                    #该文本为角色朗读的语句
                    if result_text.__contains__("“") or result_text.__contains__('"') or result_text.__contains__('「') :
                        print("是角色的语句")
                        result_text = result_text.replace("「", "").replace("」", "").replace("”", "").replace("”","").replace(
                            "？", "").replace("?", "").replace("!", "").replace("！", "")
                        if result_text == "":
                            continue
                        wav = lux_tts.generate_speech(result_text, role_prompt_id, num_steps=num_steps, t_shift=t_shift,
                                                        speed=speed, return_smooth=return_smooth)
                    else:
                        print("是旁白的语句")
                        wav = lux_tts.generate_speech(result_text, narration_prompt_id, num_steps=num_steps, t_shift=t_shift,
                                                      speed=speed, return_smooth=return_smooth)
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    # temp_save_wav_file_path = temp_path / f"{chapter_name}-{index}.wav"
                    temp_save_wav_file_path = str(temp_save_wav_file_path).replace(".wav","")+f"-{result_index}.wav"
                    wav = wav.numpy().squeeze()
                    sf.write(temp_save_wav_file_path, wav, sample_rate)
                    wav_file_path_list.append(temp_save_wav_file_path)
                    wav_duration = len(wav) / sample_rate
                    generate_chapter_audio_duration += wav_duration
                # async for data in tqdm(
                #         server.generate(
                #             target_text=chapter_text,
                #             cfg_value=2,
                #             prompt_id=role_prompt_id,
                #         )
                # ):
                #     buf.append(data)
                # wav = np.concatenate(buf, axis=0)
                # sf.write(temp_save_wav_file_path, wav, sample_rate)
                # wav_file_path_list.append(temp_save_wav_file_path)
                # wav_duration = wav.shape[0] / sample_rate
                # generate_chapter_audio_duration += wav_duration

            wav_duration = wav_duration if wav_duration > 0 else 0.1
            end_time = time.time() -start_time
            generate_chapter_audio_time += end_time
            print(f"给 {novel_name} 的 {chapter_role.get("role_name")} 分配 {chapter_role.get("bind_role_audio_name")}")
            log(f"给 {novel_name} 的 {chapter_role.get("role_name")} 分配 {chapter_role.get("bind_role_audio_name")}")
            print(f"生成音频的时长：{str(wav_duration)}，用时：{str(end_time)}，RTF：{str( end_time / wav_duration)}，当前进度：{str(index+1)}/{str(len(chapter_role_list))}")
            log(f"生成音频的时长：{str(wav_duration)}，用时：{str(end_time)}，RTF：{str( end_time / wav_duration)}，当前进度：{str(index+1)}/{str(len(chapter_role_list))}")
            
            # 让出控制权，允许取消事件被处理
            await asyncio.sleep(0)
            
            # 再次检查是否被取消（在生成一句后立即检查）
            if cancel_event and cancel_event.is_set():
                log(f"⚠️ ⚠️ 章节生成任务在第 {index+1}/{len(chapter_role_list)} 句生成后被取消 (novel_name={novel_name}, novel_id={novel_id})")
                # 清理已生成的临时文件
                for temp_file in wav_file_path_list:
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    except:
                        pass
                return False
            
            log(f"✅ [{novel_name}] 完成生成第 {index+1}/{len(chapter_role_list)} 句")
        
        # 检查是否在合并前被取消
        if cancel_event and cancel_event.is_set():
            log(f"⚠️ 章节生成任务在合并前被取消 (novel_name={novel_name}, novel_id={novel_id})")
            # 清理已生成的临时文件
            for temp_file in wav_file_path_list:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass
            return False
        
        # 根据分片列表合并wav文件
        merge_wav_files_without_resampling(wav_file_path_list,save_chapter_file_path,sample_rate)
        print(f"生成章节的时长：{str(generate_chapter_audio_duration)}，总用时：{str(generate_chapter_audio_time)}，RTF：{str(generate_chapter_audio_time / generate_chapter_audio_duration)}")
        log(f"生成章节的时长：{str(generate_chapter_audio_duration)}，总用时：{str(generate_chapter_audio_time)}，RTF：{str(generate_chapter_audio_time / generate_chapter_audio_duration)}")
        print("*"*88)
        log("*"*88)
        return True
    except Exception as e:
        log_error(f"generate_chapter_audio 生成章节音频失败 (novel_name={novel_name}, novel_id={novel_id}): {str(e)}")
        traceback.print_exc()
        return False

async def generate_chapter_audio_test(chapter_role_list,role_audio_id,novel_name,server):
    try:
        temp_path = ROOT_DIR / "temp"
        save_chapter_audio_path = ROOT_DIR / f"save/{novel_name}"
        if not os.path.exists(save_chapter_audio_path):
            os.mkdir(save_chapter_audio_path)


        # 获取对应小说的旁白的声音
        narration_role = Role.select().where(
            (Role.novel_name == novel_name)&
            (Role.role_name == "旁白")
        ).get_or_none()
        print(f"获取旁白声音成功生成旁白声音成功：{narration_role.role_name}-绑定的声音：{narration_role.bind_audio_name}")
        log(f"获取旁白声音成功生成旁白声音成功：{narration_role.role_name}-绑定的声音：{narration_role.bind_audio_name}")
        narration_role_audio = RoleAudio.select().where(
            RoleAudio.role_name == narration_role.bind_audio_name
        ).get_or_none()
        print("获取旁白角色音频成功")
        log("获取旁白角色音频成功")
        with open(narration_role_audio.audio_path, "rb") as f:
            narration_wav_bytes = f.read()

        print("读取角色音频文件成功")
        log("读取角色音频文件成功")
        # narration_prompt_id = await server.add_prompt(
        #     wav=narration_wav_bytes,
        #     wav_format="wav",  # 指定格式
        #     prompt_text=narration_role_audio.audio_text
        # )
        # model_info = await server.get_model_info()
        # sample_rate = int(model_info["sample_rate"])
        wav_file_path_list = []
        for (index,chapter_role) in enumerate(chapter_role_list):
            role_prompt_id = ""
            buf = []
            #生成旁白声音
            if chapter_role.get("type") == "narration":
                # async for data in tqdm(
                #         server.generate(
                #             target_text=chapter_role.get("text"),
                #             cfg_value=2,
                #             prompt_id=narration_prompt_id,
                #         )
                # ):
                #     buf.append(data)
                # wav = np.concatenate(buf, axis=0)
                save_wav_file_path = temp_path / f"{chapter_role_list[0]}-index.wav"
                # sf.write(save_wav_file_path, wav, sample_rate)
                wav_file_path_list.append(save_wav_file_path)
                print(f"这时旁白的声音：{chapter_role.get('text')}")
                log(f"这时旁白的声音：{chapter_role.get('text')}")
                continue
            #生成角色声音
            elif chapter_role.get("type") == "role":
                role_name = chapter_role.get("role_name")
                role_prompt_id = ""
                for prompt_id in role_audio_id:
                    #如果生成的角色声音在预加载的角色声音列表里面，则加载角色音频id
                    if role_name == prompt_id.get("audio_role_name"):
                        role_prompt_id = prompt_id.get("prompt_id")
                        break
                    #如果不存在角色预加载音频里面，则从根据角色名数据库预加载
                    """
                    这里假设传入的chapter_role_list列表是[{
                    "role_name": "张三",
                    "type": "narration或role",
                    "bind_role_audio_name": "素琴",
                    "text":"小说内容"
                    }]
                    """
                if role_prompt_id == "":
                    role_audio_data = RoleAudio.get(role_name=chapter_role.get("bind_role_audio_name"))
                    with open(role_audio_data.audio_path, "rb") as f:
                        role_wav_bytes = f.read()
                    print(f"该句的类型是角色：{chapter_role.get('text')}")
                    log(f"该句的类型是角色：{chapter_role.get('text')}")
                    # role_prompt_id = await server.add_prompt(
                    #     wav=role_wav_bytes,
                    #     wav_format="wav",  # 指定格式
                    #     prompt_text=role_audio_data.audio_text
                    # )
                # async for data in tqdm(
                #         server.generate(
                #             target_text=chapter_role.get("text"),
                #             cfg_value=2,
                #             prompt_id=role_prompt_id,
                #         )
                # ):
                #     buf.append(data)
                # wav = np.concatenate(buf, axis=0)
                save_wav_file_path = temp_path / f"{chapter_role_list[0]}-index.wav"
                # sf.write(save_wav_file_path, wav, sample_rate)
                wav_file_path_list.append(save_wav_file_path)
        # 根据分片列表合并wav文件
        # merge_wav_files_without_resampling(wav_file_path_list,save_wav_file_path /f"{novel_name}.wav",sample_rate)
        print("句子判断完毕")
        log("句子判断完毕")
        print(wav_file_path_list)
        log(str(wav_file_path_list))
        print("*"*80)
        log("*"*80)
        return True
    except Exception as e:
        log_error(f"generate_chapter_audio_test 生成章节音频测试失败 (novel_name={novel_name}): {str(e)}")
        traceback.print_exc()
        return False
if __name__ == '__main__':
    # folder_path = './audios'
    # role_name_list = get_folders(folder_path)
    # for role_name in role_name_list:
    #     with open(f"{folder_path}/{role_name}/gender.txt", "r", encoding="utf-8") as f:
    #         role_gender = f.read()
    #     with open(f"{folder_path}/{role_name}/text.txt", "r", encoding="utf-8") as f:
    #         audio_text = f.read()
    #     audio_path = ROOT_DIR / f"audios/{role_name}/audio.wav"
    #     audio_uri = f"{role_name}/audio.wav"
    #     old_role = RoleAudio.get_or_none(RoleAudio.role_name == role_name)
    #     # 如果角色不存在，则添加角色
    #     if old_role is None:
    #         print(f"扫描到当前角色名 {role_name} 不在数据表中，添加数据：")
    result = extract_dialogue_and_narration("盛元瑶：「」")
    print("「」".__contains__('「'))
    pass

