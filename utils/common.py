import json
import re
import traceback
import anthropic
from pathlib import Path

config_path = Path(__file__).resolve().parent.parent / "config/lively_config.json"

_db = None

def get_db():
    global _db
    if _db is None:
        from bean.beans import get_db as _get_db
        _db = _get_db()
    return _db
db = get_db()
def get_novel_name(novel_path):

    path = Path(novel_path)
    # 获取文件名（不包含扩展名）
    return path.stem  # "三体"




def array_to_obj_list(start,array):
    obj_list = []
    index = 0
    for i in range(start,start+len(array)):
        obj = {str(i):array[index]}
        obj_list.append(obj)
        index += 1
    return obj_list

def sum_text_len(text_section):
    text_len = 0
    for text in text_section:
        text_len += len(text)
    return text_len


def split_novel_text(novel_path):
    if novel_path == "":
        return False
    source_path = novel_path

    section_re = re.compile(r'^.*[\s]*[第][0-9零一二三四五六七八九十百千万]+[章]\s*.{1,20}$')
    input_novel_text_list = open(source_path, 'r', encoding='utf-8').readlines()

    temp_max_section_text_list = []
    max_section_text_obj_list = []
    chapter_text_list = []
    i = 0

    import utils.config as config
    from bean.beans import Novel, NovelName, Role

    try:
        get_db().begin()
        novel_name = get_novel_name(novel_path)
        NovelName.create(
            novel_name=novel_name
        )
        Role.create(
            role_name="旁白",
            novel_name=novel_name,
            role_count=1,
            gender="无",
            is_bind=False,
            bind_audio_name="",
            chapter_count=0,
            presence_rate=0,
        )
        chapter_names = ""
        chapter_names_list = []
        for (index,line) in enumerate(input_novel_text_list):
            if re.match(section_re, line):
                line = re.sub(r'\s+', ' ', line)
                chapter_name = re.sub('(~+|\\*+|\\,+|\\?+|\\，+|\\?+)', '_', line)
                chapter_names_list.append(chapter_name)
                if len(chapter_text_list) == 0:
                    chapter_text_list.append(chapter_name)
                else:
                    chapter_names += f"[{chapter_name}] "
                    max_section_text_list_len = 0
                    if len(temp_max_section_text_list) != 0:
                        max_section_text_list_len = sum_text_len(temp_max_section_text_list)
                    chapter_text_list_len = sum_text_len(chapter_text_list)
                    if ((max_section_text_list_len + chapter_text_list_len) < config.load_config(config_path,"character_segmentation_size")) or max_section_text_list_len == 0:
                        temp_max_section_text_list.extend(chapter_text_list)
                        max_section_text_obj_list.extend(array_to_obj_list(len(max_section_text_obj_list), chapter_text_list))
                        chapter_text_list = []
                        chapter_text_list.append(chapter_name)
                    else:
                        print("小说章节名列表：")
                        print(chapter_names_list)
                        print("小说章节名："+chapter_names)
                        Novel.create(
                            section_data_json=json.dumps(max_section_text_obj_list,ensure_ascii=False),
                            after_analysis_data_json="",
                            novel_name=novel_name,
                            current_state=1,
                            chapter_names = chapter_names
                        )
                        chapter_names = ""
                        chapter_names_list = []
                        temp_max_section_text_list = []
                        max_section_text_obj_list = []
                        max_section_text_obj_list.extend(array_to_obj_list(len(max_section_text_obj_list), chapter_text_list))
                        temp_max_section_text_list.extend(chapter_text_list)
                        chapter_text_list = []
                        chapter_text_list.append(chapter_name)

                i+=1
            else:
                line = line.replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '')
                if line != "":
                    chapter_text_list.append(line)
                if index == len(input_novel_text_list)-1:
                    max_section_text_obj_list.extend(array_to_obj_list(len(max_section_text_obj_list), chapter_text_list))
                    Novel.create(
                        section_data_json=json.dumps(max_section_text_obj_list,ensure_ascii=False),
                        after_analysis_data_json="",
                        novel_name=novel_name,
                        current_state=1,
                        chapter_names = chapter_names
                    )
                    chapter_names = ""
                    chapter_text_list = []
                    temp_max_section_text_list = []
        db.commit()
    except Exception as e:
        print(e)
        traceback.print_exc()
        db.rollback()



def model_parse(prompt):
    print(prompt)

    import utils.config as config

    client = anthropic.Anthropic(
        api_key=config.load_config(config_path,"api_key"),
        base_url=config.load_config(config_path,"base_url")
    )
    max_tokens = config.load_config(config_path,"max_tokens")
    if max_tokens == "":
        max_tokens = 8192
    full_response_text = ""
    with client.messages.stream(
            model=config.load_config(config_path,"model_name"),
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ],
            system="你是一位小说信息识别请，请解析我发给你的规则和json文本，只需要将json结果返回给我即可，请注意，你只需要发送纯粹的json字符串即可，不需要md格式的，我需要配合程序解析"
    ) as stream:
        for text in stream.text_stream:
            full_response_text += text
            print(text, end="", flush=True)

    return json.loads(full_response_text)


def parse_novel_text():
    """
    将分割的小说文本，加上提示词，发送给ai解析
    :return:
    """
    from bean.beans import Novel, NovelName, Role

    novel_name = NovelName.select().limit(1).get()
    novel_list = Novel.select().where(
        (Novel.novel_name == novel_name.novel_name) &
        (Novel.current_state == 1)
    ).limit(15)

    with open("../asset/prompt.txt", "r", encoding="utf-8") as file:
        prompt_text = file.read()
    novel_list = list(novel_list)
    index = 0
    while index < len(novel_list):
        try:
            new_prompt_text = prompt_text + novel_list[index].section_data_json
            parse_text_json = model_parse(new_prompt_text)

            get_db().begin()
            role_chapter_max = Role.select().where(
                Role.novel_name == novel_name.novel_name
            ).order_by(Role.create_time.asc()).limit(1).get_or_none()
            role_chapter_max_count = role_chapter_max.chapter_count
            print("查询到的最大章节次数："+str(role_chapter_max_count))
            for role in parse_text_json["roleList"]:
                old_role = Role.get_or_none(
                    (Role.role_name == role["roleName"]) &
                    (Role.novel_name == novel_name.novel_name)
                )

                if not old_role:
                    temp_role = Role.create(
                        role_name=role["roleName"],
                        novel_name=novel_name.novel_name,
                        role_count=role["count"],
                        gender=role["gender"],
                        is_bind=False,
                        bind_audio_name="",
                        chapter_count=role_chapter_max_count + 1
                    )
                    print("添加的角色的章节次数："+str(temp_role.chapter_count))
                    print(temp_role.__data__)
                else:
                    old_role.role_count = old_role.role_count + role["count"]
                    old_role.chapter_count = role_chapter_max.chapter_count + 1
                    old_role.save()
                    print("保存的角色的章节次数："+str(old_role.chapter_count))
                    print(old_role.__data__)
            print("-----------------------------")
            role_chapter_max.chapter_count = role_chapter_max.chapter_count + 1
            role_chapter_max.save()

            novel_list[index].after_analysis_data_json = json.dumps(parse_text_json["sentenceList"], ensure_ascii=False)
            novel_list[index].current_state = 2
            novel_list[index].save()
            db.commit()
            index += 1
        except Exception as e:
            traceback.print_exc()
            get_db().rollback()

def split_novel_text2(novel_path):
    if novel_path == "":
        return False
    source_path = novel_path

    section_re = re.compile(r'^.*[\s]*[第][0-9零一二三四五六七八九十百千万]+[章]\s*.{1,20}$')
    input_novel_text_list = open(source_path, 'r', encoding='utf-8').readlines()

    temp_max_section_text_list = []
    max_section_text_obj_list = []
    chapter_text_list = []
    novel_name = get_novel_name(novel_path)
    chapter_names = ""
    chapter_text_array = []

    import utils.config as config
    from bean.beans import Novel, NovelName, Role

    for (index,line) in enumerate(input_novel_text_list):
        if re.match(section_re, line):
            line = re.sub(r'\s+', ' ', line)
            chapter_name = re.sub('(~+|\\*+|\\,+|\\?+|\\，+|\\?+)', '_', line)
            if len(chapter_text_list) == 0:
                chapter_text_list.append(chapter_name)
            else:
                chapter_names += f"[{chapter_name}] "
                chapter_text_array.append(chapter_text_list)
                chapter_text_list = []
                chapter_text_list.append(chapter_name)
        else:
            line = line.replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '')
            if line != "":
                chapter_text_list.append(line)
            if index == len(input_novel_text_list)-1:
                chapter_text_array.append(chapter_text_list)
                chapter_names = ""
                chapter_text_list = []
        temp_max_section_text_list = []
        chapter_names = ""
    try:
        db.begin()
        novel_name = get_novel_name(novel_path)
        NovelName.create(
            novel_name=novel_name
        )
        Role.create(
            role_name="旁白",
            novel_name=novel_name,
            role_count=1,
            gender="无",
            is_bind=False,
            bind_audio_name="",
            chapter_count=0,
            presence_rate=0,
        )
        for (i,chapter_text) in enumerate(chapter_text_array):
            if len(temp_max_section_text_list) == 0:
                temp_max_section_text_list.extend(chapter_text)
                chapter_names += f"[{chapter_text[0]}]"
                continue
            top_chapter_text_len = sum_text_len(temp_max_section_text_list)
            current_chapter_text_len = sum_text_len(chapter_text)
            character_segmentation_size = config.load_config(config_path,"character_segmentation_size")
            if  top_chapter_text_len+ current_chapter_text_len > character_segmentation_size:
                max_section_text_obj_list = array_to_obj_list(0,temp_max_section_text_list)
                Novel.create(
                    section_data_json=json.dumps(max_section_text_obj_list, ensure_ascii=False),
                    after_analysis_data_json="",
                    novel_name=novel_name,
                    current_state=1,
                    chapter_names=chapter_names
                )
                temp_max_section_text_list = []
                chapter_names = f"[{chapter_text[0]}]"
                temp_max_section_text_list.extend(chapter_text)
                if i == len(chapter_text_array) - 1:
                    print("到达最后一章节")
                    max_section_text_obj_list = array_to_obj_list(0, temp_max_section_text_list)
                    Novel.create(
                        section_data_json=json.dumps(max_section_text_obj_list, ensure_ascii=False),
                        after_analysis_data_json="",
                        novel_name=novel_name,
                        current_state=1,
                        chapter_names=chapter_names
                    )
                continue

            temp_max_section_text_list.extend(chapter_text)
            chapter_names += f" [{chapter_text[0]}]"
            if i == len(chapter_text_array) - 1:
                max_section_text_obj_list = array_to_obj_list(0, temp_max_section_text_list)
                Novel.create(
                    section_data_json=json.dumps(max_section_text_obj_list, ensure_ascii=False),
                    after_analysis_data_json="",
                    novel_name=novel_name,
                    current_state=1,
                    chapter_names=chapter_names
                )
        db.commit()
    except Exception as e:
        traceback.print_exc()
        get_db().rollback()


def split_novel_text_by_content_list(novel_content_list,novel_name):
    if len(novel_content_list) == 0:
        return False

    section_re = re.compile(r'^.*[\s]*[第][0-9零一二三四五六七八九十百千万]+[章]\s*.{1,20}$')
    input_novel_text_list = novel_content_list

    temp_max_section_text_list = []
    chapter_text_list = []
    chapter_names = ""
    chapter_text_array = []

    import utils.config as config
    from bean.beans import Novel, NovelName, Role

    for (index, line) in enumerate(input_novel_text_list):
        if re.match(section_re, line):
            line = re.sub(r'\s+', ' ', line)
            chapter_name = re.sub('(~+|\\*+|\\,+|\\?+|\\，+|\\?+)', '_', line)
            if len(chapter_text_list) == 0:
                chapter_text_list.append(chapter_name)
            else:
                chapter_names += f"[{chapter_name}] "
                chapter_text_array.append(chapter_text_list)
                chapter_text_list = []
                chapter_text_list.append(chapter_name)
        else:
            line = line.replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '')
            if line != "":
                chapter_text_list.append(line)
            if index == len(input_novel_text_list) - 1:
                chapter_text_array.append(chapter_text_list)
                chapter_names = ""
                chapter_text_list = []
        temp_max_section_text_list = []
        chapter_names = ""
    try:
        db.begin()
        NovelName.create(
            novel_name=novel_name
        )
        Role.create(
            role_name="旁白",
            novel_name=novel_name,
            role_count=1,
            gender="无",
            is_bind=False,
            bind_audio_name="",
            chapter_count=0,
            presence_rate=0,
        )
        for (i, chapter_text) in enumerate(chapter_text_array):
            if len(temp_max_section_text_list) == 0:
                temp_max_section_text_list.extend(chapter_text)
                chapter_names += f"[{chapter_text[0]}]"
                continue
            top_chapter_text_len = sum_text_len(temp_max_section_text_list)
            current_chapter_text_len = sum_text_len(chapter_text)
            character_segmentation_size = config.load_config(config_path, "max_section_length")
            if top_chapter_text_len + current_chapter_text_len > character_segmentation_size:
                max_section_text_obj_list = array_to_obj_list(0, temp_max_section_text_list)
                Novel.create(
                    section_data_json=json.dumps(max_section_text_obj_list, ensure_ascii=False),
                    after_analysis_data_json="",
                    novel_name=novel_name,
                    current_state=1,
                    chapter_names=chapter_names
                )
                temp_max_section_text_list = []
                chapter_names = f"[{chapter_text[0]}]"
                temp_max_section_text_list.extend(chapter_text)
                if i == len(chapter_text_array) - 1:
                    print("到达最后一章节")
                    max_section_text_obj_list = array_to_obj_list(0, temp_max_section_text_list)
                    Novel.create(
                        section_data_json=json.dumps(max_section_text_obj_list, ensure_ascii=False),
                        after_analysis_data_json="",
                        novel_name=novel_name,
                        current_state=1,
                        chapter_names=chapter_names
                    )
                continue

            temp_max_section_text_list.extend(chapter_text)
            chapter_names += f" [{chapter_text[0]}]"
            if i == len(chapter_text_array) - 1:
                max_section_text_obj_list = array_to_obj_list(0, temp_max_section_text_list)
                Novel.create(
                    section_data_json=json.dumps(max_section_text_obj_list, ensure_ascii=False),
                    after_analysis_data_json="",
                    novel_name=novel_name,
                    current_state=1,
                    chapter_names=chapter_names
                )
        db.commit()
    except Exception as e:
        traceback.print_exc()
        get_db().rollback()
if __name__ == '__main__':
    # TODO 添加数据时，得判断小说名是否存在
    novel_path = "沧元图.txt"
    # novel_path = "D:\\Projects\\Python\\lively\\utils\\test.txt"
    # split_novel_text2(novel_path)

    # parse_novel_text()

