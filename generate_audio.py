import os
from pathlib import Path

from bean.beans import RoleAudio, Role
from utils.config import load_config
config_path = Path(__file__).resolve().parent / "config/lively_config.json"

async def load_role_audio(novel_name,server):
    """
    加载前x个主要角色到内存中，提高音频生成速度
    :param novel_name: 需要加载角色的小说名字
    :param server: nanollm_voxcpe的模型对象
    :return:
    """
    # 加载配置信息
    load_role_count = load_config(config_path,"load_role_count")
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
        audio_role_name_list.append(role.role_name)
    audio_role_list = RoleAudio.select().where(RoleAudio.role_name.in_(audio_role_name_list))
    load_role_list = []
    for audio_role in audio_role_list:
        with open(audio_role.audio_path, "rb") as f:
            wav_bytes = f.read()
        prompt_id = await server.add_prompt(
            wav=wav_bytes,
            wav_format="wav",  # 指定格式
            prompt_text=audio_role.audio_text
        )
        tmep_role = {
            "role_name": audio_role.role_name,
            "prompt_id": prompt_id
        }
        load_role_list.append(tmep_role)
    return load_role_list
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
    folder_path = './audios'
    role_name_list = get_folders(folder_path)
    for role_name in role_name_list:
        with open(f"{folder_path}/{role_name}/gender.txt", "r") as f:
            role_gender = f.read()
        with open(f"{folder_path}/{role_name}/text.txt", "r") as f:
            audio_text = f.read()
        audio_path = f"{folder_path}/{role_name}/audio.wav"
        old_role = Role.get_or_none(Role.role_name == role_name)
        # 如果角色不存在，则添加角色
        if old_role is None:
            RoleAudio.create(
                role_name=role_name,
                gender=role_gender,
                audio_text=audio_text,
                audio_path=audio_path,
                citaion_count = 0
            )