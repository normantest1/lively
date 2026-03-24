from pathlib import Path
from peewee import *
import datetime
from pydantic import BaseModel as PydanticBaseModel
config_path = Path(__file__).resolve().parent.parent / "config/lively_config.json"
def init_db():
    import utils.config as config

    db = SqliteDatabase(
        config.load_config(config_path,"database_name")+'.db',
        pragmas={
        'journal_mode': 'wal',  # 写前日志，提高并发
        'cache_size': -1024 * 64,  # 64MB缓存
        'foreign_keys': 1,  # 启用外键约束
        'ignore_check_constraints': 0,
        'synchronous': 0  # 平衡性能和数据安全
    })
    return db
db = init_db()
class BaseModel(Model):
    class Meta:
        database = db

class Novel(BaseModel):
    id = AutoField(primary_key=True)
    chapter_names = TextField(verbose_name="分片小说的章节名")
    section_data_json = TextField(verbose_name="分片数据，负责传给大模型分析的")
    after_analysis_data_json = TextField(verbose_name="大模型解析后的数据")
    create_time = DateTimeField(default=datetime.datetime.now, verbose_name="创建时间")
    novel_name = CharField(max_length=100,verbose_name="小说名")
    current_state = IntegerField(verbose_name="当前数据状态，1 已分片待解析，2 已解析待合成，3 已合成语音")
    class Meta:
        table_name = 'novels'
        order_by = ('create_time',)
        indexes = (
            (('novel_name', 'current_state'), False),  # 复合索引
        )

class Role(BaseModel):
    id = AutoField(primary_key=True)
    novel_name = CharField(max_length=100,verbose_name="小说名",index=True)
    role_name = CharField(max_length=50,index=True,verbose_name="角色名称")
    role_count = IntegerField(verbose_name="角色出现次数")
    gender = CharField(max_length=2,verbose_name="角色性别")
    is_bind = BooleanField(verbose_name="是否绑定了对应的角色声音")
    bind_audio_name = CharField(max_length=100,verbose_name="对应角色声音的名称",index=True)
    chapter_count = IntegerField(verbose_name="对应章节的数量")
    presence_rate = DoubleField(verbose_name="角色出场率")
    create_time = DateTimeField(default=datetime.datetime.now, verbose_name="创建时间")
    class Meta:
        table_name = 'roles'

class NovelName(BaseModel):
    id = AutoField(primary_key=True)
    novel_name = TextField(verbose_name="小说名字",unique=True,index=True)
    create_time = DateTimeField(default=datetime.datetime.now, verbose_name="创建时间")
    class Meta:
        table_name = 'novel_names'
        order_by = ('create_time',)

class RoleAudio(BaseModel):
    id = AutoField(primary_key=True)
    role_name = TextField(verbose_name="音频角色名",unique=True,index=True)
    audio_path = TextField(verbose_name="音频文件路径")
    gender = CharField(max_length=2,verbose_name="角色性别",index=True)
    audio_text = TextField(verbose_name="角色音频的文本内容")
    citation_count = IntegerField(verbose_name="角色音频被使用的次数")
    audio_uri = TextField(verbose_name="项目播放路径")
    create_time = DateTimeField(default=datetime.datetime.now, verbose_name="创建时间")
    class Meta:
        table_name = 'role_audios'
        order_by = ('create_time',)

db.create_tables([Novel,Role,NovelName,RoleAudio])
def get_db():
    return db
