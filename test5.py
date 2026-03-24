from idlelib.outwin import file_line_progs

from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import os


def remove_silence_from_audio(
    input_path: str,
    output_path: str,
    silence_thresh: int = -40,
    min_silence_len: int = 3000,
    keep_short_silence: int = 500
) -> dict:
    """
    删除音频中的长静音部分，保留短停顿

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
        else:
            print(f"  ✗ 失败: {result['message']}")

    return results


# 测试代码
if __name__ == "__main__":
    # 测试单个文件
    test_input = "D:\\Projects\\Python\\lively\\第一章-孟川和云青萍.wav"
    test_output = "D:\\Projects\\Python\\lively\\第一章-孟川和云青萍2.wav"
    dir_path = "D:\\Projects\\Python\\lively"
    files = [f for f in os.listdir(dir_path) if os.path.isfile(f)]
    numbers = []
    print(files)
    for file in files:
        number = file.split("-")[0]
        print(number)
        numbers.append(number)
    numbers.sort()
    print(numbers)