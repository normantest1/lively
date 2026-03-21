import json
import re
import traceback
import anthropic
from bean.beans import *
from pathlib import Path
# from utils.config import load_config
import utils.config as config
config_path = Path(__file__).resolve().parent.parent / "config/lively_config.json"



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
    try:
        get_db().begin()
        novel_name = get_novel_name(novel_path)
        NovelName.create(
            novel_name=novel_name
        )
        Role.create(
            role_name="测试角色",
            novel_name=novel_name,
            role_count=1,
            gender="男",
            is_bind=False,
            bind_audio_name="",
            chapter_count=0
        )
        for (index,line) in enumerate(input_novel_text_list):
            if re.match(section_re, line):
                line = re.sub(r'\s+', ' ', line)
                chapter_name = re.sub('(~+|\\*+|\\,+|\\?+|\\，+|\\?+)', '_', line)  # 章节名字当文件名字时，不能有特殊符号
                #章节列表为空，代表还没读取到一章
                if len(chapter_text_list) == 0:
                    chapter_text_list.append(line)
                else:
                    #已经读取了一章的情况
                    # print("已经读取了一章")
                    max_section_text_list_len = 0
                    if len(temp_max_section_text_list) != 0:
                        max_section_text_list_len = sum_text_len(temp_max_section_text_list)
                    chapter_text_list_len = sum_text_len(chapter_text_list)
                    #如果已粗存的字符加上读取章节的字符小于最大分片字符数，说明还没到极限
                    #
                    if ((max_section_text_list_len + chapter_text_list_len) < config.load_config(config_path,"character_segmentation_size")) or max_section_text_list_len == 0:
                        # print("======当前章节数："+str(i))
                        # print("当前章节字符长度："+str(chapter_text_list_len))
                        # print("当前最大分片字符长度：" + str(max_section_text_list_len))

                        # print("当前最大分片字符长度+章节字符长度："+str(max_section_text_list_len + chapter_text_list_len))

                        # print("最大切片字符未达上限，添加中")

                        temp_max_section_text_list.extend(chapter_text_list)
                        #最大切片没有达到极限，将章节数据转换成对象数据[{"1","你好"},{"2","是的"},...]
                        max_section_text_obj_list.extend(array_to_obj_list(len(max_section_text_obj_list), chapter_text_list))
                        chapter_text_list = []
                        chapter_text_list.append(chapter_name)
                    #现在最大分片字符数已经到极限了，得加到数据库里面
                    else:
                        #数据保存到数据库操作
                        # print("-------当前章节数："+str(i))


                        # print("当前章节字符长度：" + str(chapter_text_list_len))
                        # print("当前最大分片字符长度：" + str(max_section_text_list_len))

                        # print("当前最大分片字符长度+章节字符长度：" + str(max_section_text_list_len + chapter_text_list_len))
                        # print(max_section_text_obj_list)
                        Novel.create(
                            section_data_json=json.dumps(max_section_text_obj_list,ensure_ascii=False),
                            after_analysis_data_json="",
                            novel_name=novel_name,
                            current_state=1,
                        )
                        # print("数据量已达到最大，保存数据中......")
                        # print("===============================")
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
                    #到达最后行数据，已经没有章节了，不走上面的逻辑，保存数据
                if index == len(input_novel_text_list)-1:
                    max_section_text_obj_list.extend(array_to_obj_list(len(max_section_text_obj_list), chapter_text_list))
                    #剩最后一章了，已读取完毕，保存最后的数据
                    # print("最后一章读取完成，保存数据.....")
                    # print(max_section_text_obj_list)
                    Novel.create(
                        section_data_json=json.dumps(max_section_text_obj_list,ensure_ascii=False),
                        after_analysis_data_json="",
                        novel_name=novel_name,
                        current_state=1
                    )
                    chapter_text_list = []
                    temp_max_section_text_list = []
        db.commit()
    except Exception as e:
        print(e)
        db.rollback()

def model_parse(prompt):
    print(prompt)
    # 构造 client
    # 初始化客户端
    client = anthropic.Anthropic(
        api_key=config.load_config(config_path,"api_key"),
        base_url=config.load_config(config_path,"base_url")
    )
    max_tokens = config.load_config(config_path,"max_tokens")
    if max_tokens == "":
        max_tokens = 8192
    full_response_text = ""
    with client.messages.stream(
            model=config.load_config(config_path,"model_name"),  # 或 claude-3-opus, claude-3-haiku
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ],
            system="你是一位小说信息识别请，请解析我发给你的规则和json文本，只需要将json结果返回给我即可，请注意，你只需要发送纯粹的json字符串即可，不需要md格式的，我需要配合程序解析"
    ) as stream:
        for text in stream.text_stream:
            full_response_text += text
            print(text, end="", flush=True)
                # text 是逐步输出的内容块 # 累积完整内容

    return json.loads(full_response_text)


def parse_novel_text():
    """
    将分割的小说文本，加上提示词，发送给ai解析
    :return:
    """
#       .读取数据库中的小说数据
#             #读取一本小说对应的所有未被解析的文本
    novel_name = NovelName.select().limit(1).get()
    novel_list = Novel.select().where(
        (Novel.novel_name == novel_name.novel_name) &
        (Novel.current_state == 1)
    ).limit(15)
    #获取小说对应的角色信息

#       .读取提示文本规则，将数据拼接到文本规则内
    with open("../asset/prompt.txt","r",encoding="utf-8") as file:
        prompt_text = file.read()
    novel_list = list(novel_list)
    index = 0
    while index < len(novel_list):
        try:
            new_prompt_text = prompt_text + novel_list[index].section_data_json
        #       .调用api让大模型解析小说文本
            parse_text_json = model_parse(new_prompt_text)

        #   .开启事务，更新角色信息与保存解析后的数据
            get_db().begin()
            role_chapter_max = Role.select().where(
                Role.novel_name == novel_name.novel_name
            ).order_by(Role.create_time.asc()).limit(1).get_or_none()
            role_chapter_max_count = role_chapter_max.chapter_count
            print("查询到的最大章节次数："+str(role_chapter_max_count))
            # 遍历获取到的所有角色，将新的角色数据添加到旧的角色数据里
            for role in parse_text_json["roleList"]:
                # 更新旧的角色数据信息
                old_role = Role.get_or_none(
                    (Role.role_name == role["roleName"]) &
                    (Role.novel_name == novel_name.novel_name)
                )

                # 如果角色信息不存在，则添加新的角色信息
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
                    # 如果角色存在，则更新角色信息
                    old_role.role_count = old_role.role_count + role["count"]
                    old_role.chapter_count = role_chapter_max.chapter_count + 1
                    old_role.save()
                    print("保存的角色的章节次数："+str(old_role.chapter_count))
                    print(old_role.__data__)
            print("-----------------------------")
            #角色章节数+1
            role_chapter_max.chapter_count = role_chapter_max.chapter_count + 1
            role_chapter_max.save()

            # 保存解析后的章节文本
            novel_list[index].after_analysis_data_json = json.dumps(parse_text_json["sentenceList"], ensure_ascii=False)
            novel_list[index].current_state = 2
            novel_list[index].save()
            db.commit()
            index += 1
        except Exception as e:
            traceback.print_exc()
            get_db().rollback()



if __name__ == '__main__':
    # TODO 添加数据时，得判断小说名是否存在
    novel_path = "D:\\Projects\\Python\\lively\\utils\\沧元图.txt"
    # novel_path = "D:\\Projects\\Python\\lively\\utils\\test.txt"
    split_novel_text(novel_path)

    # parse_novel_text()

