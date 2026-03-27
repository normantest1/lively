
import traceback
from contextlib import asynccontextmanager

from starlette.middleware.cors import CORSMiddleware

from bean.beans import RoleAudio, Role, Novel, get_db, NovelName
from logger import init_logger, log, log_error, close_logger
from fastapi import FastAPI, HTTPException, status, Query, UploadFile, WebSocket
from pydantic import BaseModel, ConfigDict
from pydantic import Field as PydanticField
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
# TODO 这里是关键注释
from nanovllm_voxcpm.models.voxcpm.server import AsyncVoxCPMServerPool
from nanovllm_voxcpm import VoxCPM

from typing import List, Optional
from peewee import *
import datetime
import json

from generate_audio import update_audio_role, load_role_audio, generate_chapter_audio
from parse_text import async_parse_text, parse_novel_data_bind_role_audio
from utils.common import split_novel_text_by_content_list
from scheduler_tasks import (
    add_parse_job,
    add_generate_job,
    remove_job,
    get_all_jobs,
    get_parse_task_status,
    get_generate_task_status,
    start_scheduler,
    execute_parse_task,
    execute_generate_task,
    set_server_instance,
    stop_scheduler,
    get_task_details,
    get_all_task_details,
    get_task_logs,
    clear_task_logs
)

db = get_db()


# 导入您的数据库模型
# from your_model_file import db, Novel, Role, NovelName, RoleAudio

# ============ Pydantic 模型定义 ============

# ============ Pydantic 模型定义（使用 V2 语法） ============

# Novel 相关的 Pydantic 模型
class NovelBase(BaseModel):
    chapter_names: str = PydanticField(..., title="章节名", description="分片小说的章节名")
    section_data_json: str = PydanticField(..., title="分片数据", description="负责传给大模型分析的")
    after_analysis_data_json: Optional[str] = PydanticField(None, title="解析后数据", description="大模型解析后的数据")
    novel_name: str = PydanticField(..., max_length=100, title="小说名")
    current_state: int = PydanticField(..., ge=1, le=3, title="当前数据状态",
                               description="1 已分片待解析，2 已解析待合成，3 已合成语音")


class NovelCreate(NovelBase):
    pass


class NovelUpdate(BaseModel):
    chapter_names: Optional[str] = PydanticField(None, title="章节名")
    section_data_json: Optional[str] = PydanticField(None, title="分片数据")
    after_analysis_data_json: Optional[str] = PydanticField(None, title="解析后数据")
    novel_name: Optional[str] = PydanticField(None, max_length=100, title="小说名")
    current_state: Optional[int] = PydanticField(None, ge=1, le=3, title="当前数据状态")


class NovelResponse(NovelBase):
    id: int
    create_time: datetime.datetime

    # Pydantic V2 使用 ConfigDict
    model_config = ConfigDict(from_attributes=True)


# Role 相关的 Pydantic 模型
class RoleBase(BaseModel):
    novel_name: str = PydanticField(..., max_length=100, title="小说名")
    role_name: str = PydanticField(..., max_length=50, title="角色名称")
    role_count: int = PydanticField(..., ge=0, title="角色出现次数")
    gender: str = PydanticField(..., max_length=2, title="角色性别")
    is_bind: bool = PydanticField(False, title="是否绑定角色声音")
    bind_audio_name: Optional[str] = PydanticField(None, max_length=100, title="角色声音名称")
    chapter_count: int = PydanticField(..., ge=0, title="对应章节数量")
    presence_rate: float = PydanticField(0.0, title="角色出场率", description="角色在小说中的出场比率")


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    novel_name: Optional[str] = PydanticField(None, max_length=100)
    role_name: Optional[str] = PydanticField(None, max_length=50)
    role_count: Optional[int] = PydanticField(None, ge=0)
    gender: Optional[str] = PydanticField(None, max_length=2)
    is_bind: Optional[bool] = None
    bind_audio_name: Optional[str] = PydanticField(None, max_length=100)
    chapter_count: Optional[int] = PydanticField(None, ge=0)
    presence_rate: Optional[float] = PydanticField(None, title="角色出场率")


class RoleResponse(RoleBase):
    id: int
    create_time: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# NovelName 相关的 Pydantic 模型
class NovelNameBase(BaseModel):
    novel_name: str = PydanticField(..., title="小说名字")


class NovelNameCreate(NovelNameBase):
    pass


class NovelNameUpdate(BaseModel):
    novel_name: Optional[str] = PydanticField(None, title="小说名字")


class NovelNameResponse(NovelNameBase):
    id: int
    create_time: datetime.datetime

    model_config = ConfigDict(from_attributes=True)


# RoleAudio 相关的 Pydantic 模型
class RoleAudioBase(BaseModel):
    role_name: str = PydanticField(..., title="音频角色名")
    audio_path: str = PydanticField(..., title="音频文件路径")
    gender: str = PydanticField(..., max_length=2, title="角色性别")
    audio_text: str = PydanticField(..., title="角色音频的文本内容")
    citation_count: int = PydanticField(0, ge=0, title="角色音频被使用的次数")
    audio_uri: str = PydanticField(None, title="项目播放路径")


class RoleAudioCreate(RoleAudioBase):
    pass


class RoleAudioUpdate(BaseModel):
    role_name: Optional[str] = PydanticField(None, title="音频角色名")
    audio_path: Optional[str] = PydanticField(None, title="音频文件路径")
    gender: Optional[str] = PydanticField(None, max_length=2, title="角色性别")
    audio_text: Optional[str] = PydanticField(None, title="角色音频的文本内容")
    citation_count: Optional[int] = PydanticField(None, ge=0, title="被使用的次数")


class RoleAudioResponse(RoleAudioBase):
    id: int
    create_time: datetime.datetime

    model_config = ConfigDict(from_attributes=True)
server = ""

# ============ FastAPI 应用 ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    global server
    """应用生命周期管理"""
    init_logger()
    log("="*80)
    log("服务器启动")
    log("="*80)

    if db.is_closed():
        print("Starting up, connecting to database...")
        log("Starting up, connecting to database...")
        db.connect()
        print("Database connected")
        log("Database connected")
    else:
        print("Database already connected")
        log("Database already connected")
    # todo 音频模型
    if server == "":
        print("加载模型......")
        log("加载模型......")
        server = AsyncVoxCPMServerPool = VoxCPM.from_pretrained(
            "./VoxCPM1.5/",
            max_num_batched_tokens=8192,
            max_num_seqs=16,
            max_model_len=4096,
            gpu_memory_utilization=0.95,
            enforce_eager=False,
            devices=[0]
        )

    set_server_instance(server)
    start_scheduler()

    yield

    # 关闭时执行
    stop_scheduler()
    if not db.is_closed():
        print("Shutting down, closing database...")
        log("Shutting down, closing database...")
        db.close()
        print("Database closed")
        log("Database closed")
    print("关闭模型......")
    log("关闭模型......")
    await server.stop()

    log("="*80)
    log("服务器关闭")
    log("="*80)
    close_logger()

# ============ FastAPI 应用 ============
app = FastAPI(
    title="Novel Audio System API",
    version="1.0.0",
    lifespan=lifespan  # 使用新的 lifespan 参数
)

# ============ 辅助函数 ============
def get_novel_or_404(novel_id: int) -> Novel:
    """获取小说，不存在时抛出404"""
    try:
        return Novel.get_by_id(novel_id)
    except Novel.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Novel with id {novel_id} not found"
        )
    except Exception as e:
        log_error(f"获取小说失败 (novel_id={novel_id}): {str(e)}")
        raise

def get_role_or_404(role_id: int) -> Role:
    """获取角色，不存在时抛出404"""
    try:
        return Role.get_by_id(role_id)
    except Role.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role with id {role_id} not found"
        )
    except Exception as e:
        log_error(f"获取角色失败 (role_id={role_id}): {str(e)}")
        raise

def get_novel_name_or_404(novel_name_id: int) -> NovelName:
    """获取小说名，不存在时抛出404"""
    try:
        return NovelName.get_by_id(novel_name_id)
    except NovelName.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NovelName with id {novel_name_id} not found"
        )
    except Exception as e:
        log_error(f"获取小说名失败 (novel_name_id={novel_name_id}): {str(e)}")
        raise

def get_role_audio_or_404(role_audio_id: int) -> RoleAudio:
    """获取角色音频，不存在时抛出404"""
    try:
        return RoleAudio.get_by_id(role_audio_id)
    except RoleAudio.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RoleAudio with id {role_audio_id} not found"
        )
    except Exception as e:
        log_error(f"获取角色音频失败 (role_audio_id={role_audio_id}): {str(e)}")
        raise
# ============ Novel CRUD API ============

@app.post("/api/novels", response_model=NovelResponse, status_code=status.HTTP_201_CREATED)
def create_novel(novel_data: NovelCreate):
    """创建小说"""
    try:
        novel = Novel(
            chapter_names=novel_data.chapter_names,
            section_data_json=novel_data.section_data_json,
            after_analysis_data_json=novel_data.after_analysis_data_json,
            novel_name=novel_data.novel_name,
            current_state=novel_data.current_state
        )
        novel.save()
        return novel
    except Exception as e:
        log_error(f"创建小说失败: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/novels", response_model=List[NovelResponse])
def get_novels(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        novel_name: Optional[str] = None,
        current_state: Optional[int] = Query(None, ge=1, le=3),
        order_by_create_time_desc: bool = False
):
    """获取小说列表，支持分页和过滤"""
    query = Novel.select()
    order_by_create_time_desc = False
    # 过滤条件
    if novel_name:
        query = query.where(Novel.novel_name.contains(novel_name))

    if current_state is not None:
        query = query.where(Novel.current_state == current_state)

    # 排序
    if order_by_create_time_desc:
        query = query.order_by(Novel.create_time.desc())
    else:
        query = query.order_by(Novel.create_time.asc())

    # 分页
    query = query.offset(skip).limit(limit)

    return list(query)


@app.get("/api/novels/{novel_id}", response_model=NovelResponse)
def get_novel(novel_id: int):
    """获取单个小说"""
    return get_novel_or_404(novel_id)


@app.put("/api/novels/{novel_id}", response_model=NovelResponse)
def update_novel(novel_id: int, novel_data: NovelUpdate):
    """更新小说"""
    novel = get_novel_or_404(novel_id)

    update_data = novel_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(novel, key, value)

    novel.save()
    return novel


@app.patch("/api/novels/{novel_id}", response_model=NovelResponse)
def partial_update_novel(novel_id: int, novel_data: NovelUpdate):
    """部分更新小说"""
    return update_novel(novel_id, novel_data)


@app.delete("/api/novels/{novel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_novel(novel_id: int):
    """删除小说"""
    novel = get_novel_or_404(novel_id)
    novel.delete_instance()
    return None


@app.delete("/api/novels/by-name/{novel_name}")
def delete_novel_by_name(novel_name: str):
    """删除小说及其所有相关数据（novel_names、novels、roles表）"""
    try:
        # 开始事务
        db.begin()

        # 删除该小说名的所有角色数据
        roles_deleted = Role.delete().where(Role.novel_name == novel_name).execute()
        print(f"删除了 {roles_deleted} 条角色数据")
        log(f"删除了 {roles_deleted} 条角色数据")

        # 删除该小说名的所有小说章节数据
        novels_deleted = Novel.delete().where(Novel.novel_name == novel_name).execute()
        print(f"删除了 {novels_deleted} 条小说章节数据")
        log(f"删除了 {novels_deleted} 条小说章节数据")

        # 删除该小说名记录
        novel_names_deleted = NovelName.delete().where(NovelName.novel_name == novel_name).execute()
        print(f"删除了 {novel_names_deleted} 条小说名记录")
        log(f"删除了 {novel_names_deleted} 条小说名记录")

        # 提交事务
        db.commit()

        print(f"成功删除小说 {novel_name} 的所有相关数据")
        log(f"成功删除小说 {novel_name} 的所有相关数据")
        return {
            "message": "删除成功",
            "deleted_data": {
                "roles": roles_deleted,
                "novels": novels_deleted,
                "novel_names": novel_names_deleted
            }
        }
    except Exception as e:
        # 回滚事务
        db.rollback()
        log_error(f"删除小说 {novel_name} 相关数据失败: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除小说相关数据失败: {str(e)}"
        )


@app.get("/api/novels/{novel_id}/state")
def get_novel_state(novel_id: int):
    """获取小说的详细状态信息"""
    novel = get_novel_or_404(novel_id)

    state_info = {
        "id": novel.id,
        "novel_name": novel.novel_name,
        "chapter_names": novel.chapter_names,
        "current_state": novel.current_state,
        "current_state_name": {
            1: "已分片待解析",
            2: "已解析待合成",
            3: "已合成语音"
        }.get(novel.current_state, "未知"),
        "create_time": novel.create_time,
        "section_data_length": len(novel.section_data_json) if novel.section_data_json else 0,
        "after_analysis_length": len(novel.after_analysis_data_json) if novel.after_analysis_data_json else 0
    }

    return {
        "message": "状态信息获取成功",
        "data": state_info
    }


class BatchUpdateStateRequest(BaseModel):
    novel_ids: List[int]
    new_state: int


@app.post("/api/novels/batch-update-state")
def batch_update_novels_state(request: BatchUpdateStateRequest):
    """批量更新小说状态"""
    try:
        novel_ids = request.novel_ids
        new_state = request.new_state

        # 查询选中的小说
        novels = Novel.select().where(Novel.id.in_(novel_ids))
        novels_list = list(novels)

        if not novels_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="未找到指定的小说"
            )

        # 检查所有小说的状态是否相同
        current_states = set(novel.current_state for novel in novels_list)
        if len(current_states) != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="所选小说的状态不同，无法批量修改"
            )

        current_state = novels_list[0].current_state

        # 如果状态是1，不允许修改
        if current_state == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="状态为1（已分片待解析）的小说不允许修改状态"
            )

        # 验证新状态是否有效（不能改为1）
        if new_state == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不允许将状态修改为1（已分片待解析）"
            )

        # 开始事务
        db.begin()

        updated_count = 0
        for novel in novels_list:
            if new_state == 1:
                # 从2降级到1：清空解析数据
                novel.after_analysis_data_json = ""
                novel.current_state = new_state
                novel.save()
                updated_count += 1

                # 更新roles表的chapter_count
                roles = Role.select().where(Role.novel_name == novel.novel_name)
                for role in roles:
                    role.chapter_count = max(0, role.chapter_count - 1)
                    role.save()

                print(f"小说 {novel.novel_name} 状态从 {current_state} 降级到 {new_state}，chapter_count减少1")
                log(f"小说 {novel.novel_name} 状态从 {current_state} 降级到 {new_state}，chapter_count减少1")

            elif new_state == 2:
                # 从3降级到2：直接修改状态
                novel.current_state = new_state
                novel.save()
                updated_count += 1

                print(f"小说 {novel.novel_name} 状态从 {current_state} 修改为 {new_state}")
                log(f"小说 {novel.novel_name} 状态从 {current_state} 修改为 {new_state}")

            elif new_state == 3:
                # 从2升级到3：直接修改状态
                novel.current_state = new_state
                novel.save()
                updated_count += 1

                print(f"小说 {novel.novel_name} 状态从 {current_state} 修改为 {new_state}")
                log(f"小说 {novel.novel_name} 状态从 {current_state} 修改为 {new_state}")

        # 提交事务
        db.commit()

        print(f"成功批量更新 {updated_count} 条小说数据的状态")
        log(f"成功批量更新 {updated_count} 条小说数据的状态")

        return {
            "message": "批量更新成功",
            "updated_count": updated_count,
            "old_state": current_state,
            "new_state": new_state
        }

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        log_error(f"批量更新小说状态失败: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量更新小说状态失败: {str(e)}"
        )


@app.get("/api/novel/max-chapter-count")
def get_max_chapter_count(novel_name: str = Query(..., description="小说名称")):
    """获取指定小说在current_state=2时的最大章节数"""
    try:
        max_count = Novel.select().where((Novel.novel_name == novel_name) & (Novel.current_state == 2)).count()

        return max_count
    except Exception as e:
        print(f"获取最大章节数失败: {e}")
        log(f"获取最大章节数失败: {e}")
        log_error(f"获取最大章节数失败: {str(e)}")
        return 0


@app.post("/api/novels/batch-generate")
async def batch_generate_novel(novel_name: str, chapter_count: int):
    """批量生成小说音频

    参数：
    - novel_name: 小说名称
    - chapter_count: 生成的章节数

    功能：
    1. 接收参数并打印
    2. 实时发送日志到前端
    """
    print("*" * 50)
    log("*" * 50)
    print("开始批量生成小说")
    log("开始批量生成小说")
    print(f"小说名称: {novel_name}")
    log(f"小说名称: {novel_name}")
    print(f"章节数: {chapter_count}")
    log(f"章节数: {chapter_count}")
    print("*" * 50)
    log("*" * 50)

    async def log_to_frontend(message):
        """将日志消息发送到WebSocket前端"""
        try:
            await manager.send_message(message + "\n")
        except Exception as e:
            print(f"发送日志到前端失败: {e}")
            log(f"发送日志到前端失败: {e}")
            log_error(f"发送日志到前端失败: {str(e)}")

    # 修改这里：添加批量生成的逻辑
    # 例如：
    # - 根据小说名查询数据库
    # - 获取需要生成的章节
    # - 调用TTS生成音频
    # - 更新数据库状态

    print(f"开始生成任务...")
    log(f"开始生成任务...")
    await log_to_frontend(f"开始为小说 '{novel_name}' 生成 {chapter_count} 个章节的音频...")

    # ============ 修改这里开始 ============
    # 在这里添加你的生成逻辑
    # 例如：

    try:
        # 1. 查询数据库获取小说信息
        novels = Novel.select().where(Novel.novel_name == novel_name, Novel.current_state == 2).limit(chapter_count).limit(chapter_count)
        # TODO 记得修改386行和392行的注释
        load_role_list = []
        load_role_list = await load_role_audio(novel_name, server)
        for novel in novels:
            chapter_parse_obj_list = parse_novel_data_bind_role_audio(novel.section_data_json,novel.after_analysis_data_json,novel.novel_name)
            # print("*" * 80)
            # print(chapter_parse_obj_list)
            # print("*"*80)
            # await generate_chapter_audio_test(chapter_parse_obj_list, load_role_list, novel_name, server)
        #     TODO 这里需要修改
            flag = await generate_chapter_audio(chapter_parse_obj_list,load_role_list,novel_name,novel.id,server)
            if flag:
               print(f"小说 {novel.novel_name} 章节 {novel.chapter_names} 生成完成，请去项目目录下的save文件夹下查看")
               log(f"小说 {novel.novel_name} 章节 {novel.chapter_names} 生成完成，请去项目目录下的save文件夹下查看")
               novel.current_state = 3
               novel.save()
            else:
                print(f"小说 {novel.novel_name} 章节 {novel.chapter_names} 生成失败，请重试")
                log(f"小说 {novel.novel_name} 章节 {novel.chapter_names} 生成失败，请重试")
    except Exception as e:
        print(f"批量生成小说时出错: {str(e)}")
        log(f"批量生成小说时出错: {str(e)}")
        log_error(f"批量生成小说时出错: {str(e)}")
        traceback.print_exc()


            #
    # 2. 遍历章节生成音频
    # for i, novel in enumerate(novels[:chapter_count]):
    #     await log_to_frontend(f"正在生成第 {i+1}/{chapter_count} 个章节...")
    #     # 调用音频生成逻辑
    #     await generate_audio_for_chapter(novel)
    #
    # 3. 更新数据库状态
    # ============ 修改这里结束 ============

    await log_to_frontend("所有章节音频生成完成！")
    print("批量生成完成")
    log("批量生成完成")

    return {
        "message": "批量生成任务已完成",
        "novel_name": novel_name,
        "chapter_count": chapter_count,
        "status": "success"
    }


# ============ Role CRUD API ============

@app.post("/api/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
def create_role(role_data: RoleCreate):
    """创建角色"""
    try:
        # 检查角色名在同一个小说中是否已存在
        if Role.select().where(
                (Role.novel_name == role_data.novel_name) &
                (Role.role_name == role_data.role_name)
        ).exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role {role_data.role_name} already exists in novel {role_data.novel_name}"
            )

        role = Role(**role_data.dict())
        role.save()
        return role
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"创建角色失败: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/roles", response_model=List[RoleResponse])
def get_roles(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        novel_name: Optional[str] = None,
        role_name: Optional[str] = None,
        gender: Optional[str] = Query(None, max_length=2),
        is_bind: Optional[bool] = None
):
    """获取角色列表，支持分页和过滤，按出场率降序排序"""
    query = Role.select()

    # 过滤条件
    if novel_name:
        query = query.where(Role.novel_name.contains(novel_name))

    if role_name:
        query = query.where(Role.role_name.contains(role_name))

    if gender:
        query = query.where(Role.gender == gender)

    if is_bind is not None:
        query = query.where(Role.is_bind == is_bind)

    # 按出场率降序排序
    query = query.order_by(Role.presence_rate.desc())

    # 分页
    query = query.offset(skip).limit(limit)

    return list(query)


@app.get("/api/roles/{role_id}", response_model=RoleResponse)
def get_role(role_id: int):
    """获取单个角色"""
    return get_role_or_404(role_id)


@app.put("/api/roles/{role_id}", response_model=RoleResponse)
def update_role(role_id: int, role_data: RoleUpdate):
    """更新角色"""
    role = get_role_or_404(role_id)

    update_data = role_data.dict(exclude_unset=True)

    # 如果更新角色名，检查唯一性
    if 'role_name' in update_data and 'novel_name' in update_data:
        if Role.select().where(
                (Role.novel_name == update_data.get('novel_name', role.novel_name)) &
                (Role.role_name == update_data['role_name']) &
                (Role.id != role_id)
        ).exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role name already exists in this novel"
            )

    for key, value in update_data.items():
        setattr(role, key, value)

    role.save()
    return role


@app.patch("/api/roles/{role_id}", response_model=RoleResponse)
def partial_update_role(role_id: int, role_data: RoleUpdate):
    """部分更新角色"""
    return update_role(role_id, role_data)


@app.delete("/api/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role(role_id: int):
    """删除角色"""
    role = get_role_or_404(role_id)
    role.delete_instance()
    return None


# ============ NovelName CRUD API ============

@app.post("/api/novel-names", response_model=NovelNameResponse, status_code=status.HTTP_201_CREATED)
def create_novel_name(novel_name_data: NovelNameCreate):
    """创建小说名"""
    try:
        # 检查小说名是否已存在
        if NovelName.select().where(NovelName.novel_name == novel_name_data.novel_name).exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Novel name {novel_name_data.novel_name} already exists"
            )

        novel_name = NovelName(**novel_name_data.dict())
        novel_name.save()
        return novel_name
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"创建小说名失败: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/novel-names", response_model=List[NovelNameResponse])
def get_novel_names(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        novel_name: Optional[str] = None
):
    """获取小说名列表，支持分页和过滤"""
    query = NovelName.select()

    if novel_name:
        query = query.where(NovelName.novel_name.contains(novel_name))

    query = query.order_by(NovelName.create_time.desc())
    query = query.offset(skip).limit(limit)

    return list(query)


@app.get("/api/novel-names/{novel_name_id}", response_model=NovelNameResponse)
def get_novel_name(novel_name_id: int):
    """获取单个小说名"""
    return get_novel_name_or_404(novel_name_id)


@app.put("/api/novel-names/{novel_name_id}", response_model=NovelNameResponse)
def update_novel_name(novel_name_id: int, novel_name_data: NovelNameUpdate):
    """更新小说名"""
    novel_name = get_novel_name_or_404(novel_name_id)

    if novel_name_data.novel_name:
        # 检查新名字是否已被使用
        if NovelName.select().where(
                (NovelName.novel_name == novel_name_data.novel_name) &
                (NovelName.id != novel_name_id)
        ).exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Novel name already exists"
            )
        novel_name.novel_name = novel_name_data.novel_name
        novel_name.save()

    return novel_name


@app.delete("/api/novel-names/{novel_name_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_novel_name(novel_name_id: int):
    """删除小说名"""
    novel_name = get_novel_name_or_404(novel_name_id)
    novel_name.delete_instance()
    return None


# ============ RoleAudio CRUD API ============

@app.post("/api/role-audios", response_model=RoleAudioResponse, status_code=status.HTTP_201_CREATED)
def create_role_audio(role_audio_data: RoleAudioCreate):
    """创建角色音频"""
    try:
        # 检查角色名是否已存在
        if RoleAudio.select().where(RoleAudio.role_name == role_audio_data.role_name).exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role audio for {role_audio_data.role_name} already exists"
            )

        role_audio = RoleAudio(**role_audio_data.dict())
        role_audio.save()
        return role_audio
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"创建角色音频失败: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/role-audios", response_model=List[RoleAudioResponse])
def get_role_audios(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        role_name: Optional[str] = None,
        gender: Optional[str] = Query(None, max_length=2),
        min_citation_count: Optional[int] = Query(None, ge=0)
):
    """获取角色音频列表，支持分页和过滤"""
    query = RoleAudio.select()

    if role_name:
        query = query.where(RoleAudio.role_name.contains(role_name))

    if gender:
        query = query.where(RoleAudio.gender == gender)

    if min_citation_count is not None:
        query = query.where(RoleAudio.citation_count >= min_citation_count)

    query = query.order_by(RoleAudio.create_time.desc())
    query = query.offset(skip).limit(limit)

    return list(query)


@app.get("/api/role-audios/{role_audio_id}", response_model=RoleAudioResponse)
def get_role_audio(role_audio_id: int):
    """获取单个角色音频"""
    return get_role_audio_or_404(role_audio_id)


@app.put("/api/role-audios/{role_audio_id}", response_model=RoleAudioResponse)
def update_role_audio(role_audio_id: int, role_audio_data: RoleAudioUpdate):
    """更新角色音频"""
    role_audio = get_role_audio_or_404(role_audio_id)

    update_data = role_audio_data.dict(exclude_unset=True)

    # 如果更新角色名，检查唯一性
    if 'role_name' in update_data:
        if RoleAudio.select().where(
                (RoleAudio.role_name == update_data['role_name']) &
                (RoleAudio.id != role_audio_id)
        ).exists():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Role name already exists"
            )

    for key, value in update_data.items():
        setattr(role_audio, key, value)

    role_audio.save()
    return role_audio


@app.patch("/api/role-audios/{role_audio_id}", response_model=RoleAudioResponse)
def partial_update_role_audio(role_audio_id: int, role_audio_data: RoleAudioUpdate):
    """部分更新角色音频"""
    return update_role_audio(role_audio_id, role_audio_data)


@app.delete("/api/role-audios/{role_audio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_role_audio(role_audio_id: int):
    """删除角色音频"""
    role_audio = get_role_audio_or_404(role_audio_id)
    role_audio.delete_instance()
    return None


# ============ 音频文件服务 API ============

@app.get("/api/audio/{file_path:path}")
def get_audio_file(file_path: str):
    """获取本地音频文件

    功能说明：
    - 接收前端传来的文件路径参数
    - 从本地文件系统读取音频文件
    - 返回音频文件流供前端播放
    """
    import os
    from urllib.parse import unquote

    try:
        # URL解码，恢复被编码的路径（处理中文和特殊字符）
        file_path = unquote(file_path)

        # 标准化路径，处理Windows和Unix风格
        file_path = file_path.replace('/', '\\')

        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"音频文件不存在: {file_path}"
            )

        # 检查是否为文件
        if not os.path.isfile(file_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="路径不是文件"
            )

        # 获取文件扩展名
        ext = os.path.splitext(file_path)[1].lower()

        # 支持的音频格式
        supported_formats = ['.wav', '.mp3', '.ogg', '.flac', '.m4a', '.aac']

        if ext not in supported_formats:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的音频格式: {ext}"
            )

        # 根据文件扩展名设置Content-Type
        mime_types = {
            '.wav': 'audio/wav',
            '.mp3': 'audio/mpeg',
            '.ogg': 'audio/ogg',
            '.flac': 'audio/flac',
            '.m4a': 'audio/mp4',
            '.aac': 'audio/aac'
        }

        # 使用FileResponse直接返回文件
        from fastapi.responses import FileResponse
        return FileResponse(
            path=file_path,
            media_type=mime_types.get(ext, 'application/octet-stream'),
            filename=os.path.basename(file_path)
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(f"读取音频文件失败: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"读取音频文件失败: {str(e)}"
        )


# ============ 高级查询和统计 API ============

@app.get("/api/statistics/novels-summary")
def get_novels_summary():
    """获取小说统计摘要"""

    total_novels = Novel.select().count()
    by_state = {}
    for state in [1, 2, 3]:
        count = Novel.select().where(Novel.current_state == state).count()
        state_name = {1: "已分片待解析", 2: "已解析待合成", 3: "已合成语音"}[state]
        by_state[state_name] = count

    return {
        "total_novels": total_novels,
        "by_state": by_state
    }


@app.get("/api/statistics/roles-summary")
def get_roles_summary():
    """获取角色统计摘要"""

    total_roles = Role.select().count()
    bound_roles = Role.select().where(Role.is_bind == True).count()
    unbound_roles = total_roles - bound_roles

    # 按性别统计
    gender_stats = {}
    for gender in ['男', '女']:
        count = Role.select().where(Role.gender == gender).count()
        gender_stats[gender] = count

    return {
        "total_roles": total_roles,
        "bound_roles": bound_roles,
        "unbound_roles": unbound_roles,
        "gender_distribution": gender_stats
    }


@app.get("/api/novels/{novel_id}/roles")
def get_novel_roles(novel_id: int):
    """获取指定小说的所有角色"""
    novel = get_novel_or_404(novel_id)
    roles = Role.select().where(Role.novel_name == novel.novel_name)
    return list(roles)


@app.post("/api/roles/{role_id}/bind-audio")
def bind_role_audio(role_id: int, request: dict):
    """为角色绑定音频"""
    from pydantic import BaseModel

    class BindAudioRequest(BaseModel):
        audio_name: str

    # 验证请求体
    try:
        bind_request = BindAudioRequest(**request)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请求体格式错误，需要包含 audio_name 字段"
        )

    role = get_role_or_404(role_id)
    audio_name = bind_request.audio_name

    # 检查音频是否存在
    try:
        audio = RoleAudio.get(RoleAudio.role_name == audio_name)
    except RoleAudio.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio {audio_name} not found"
        )
    except Exception as e:
        log_error(f"查询角色音频失败: {str(e)}")
        raise

    # 更新角色的绑定信息
    role.is_bind = True
    role.bind_audio_name = audio_name
    role.save()

    # 增加音频的引用计数
    audio.citation_count += 1
    audio.save()

    return {"message": f"Role {role.role_name} bound to audio {audio_name}"}


# ============ 批量操作 API ============

@app.post("/api/novels/bulk", response_model=List[NovelResponse])
def create_novels_bulk(novels_data: List[NovelCreate]):
    """批量创建小说"""
    created_novels = []

    with db.atomic():
        for novel_data in novels_data:
            novel = Novel(**novel_data.dict())
            novel.save()
            created_novels.append(novel)

    return created_novels


@app.post("/api/roles/bulk", response_model=List[RoleResponse])
def create_roles_bulk(roles_data: List[RoleCreate]):
    """批量创建角色"""
    created_roles = []

    with db.atomic():
        for role_data in roles_data:
            # 检查唯一性
            if not Role.select().where(
                    (Role.novel_name == role_data.novel_name) &
                    (Role.role_name == role_data.role_name)
            ).exists():
                role = Role(**role_data.dict())
                role.save()
                created_roles.append(role)

    return created_roles


@app.get("/api/role-audio/unbound", response_model=List[RoleAudioResponse])
def get_unbound_role_audios(novel_name: str = Query(..., description="小说名称")):
    """获取未绑定的角色音频列表，用于角色绑定音频功能

    功能说明：
    1. 根据传入的小说名，从Role表中查询该小说已绑定音频的角色名（bind_audio_name）
    2. 在RoleAudio表中查询role_name不在上述绑定列表的所有音频
    3. 返回这些未绑定的音频列表给前端
    """
    # 根据小说名查询已绑定音频的角色名
    bound_audio_names = [
        role.bind_audio_name
        for role in Role.select(Role.bind_audio_name).where(
            Role.novel_name == novel_name,
            Role.bind_audio_name.is_null(False)
        )
        if role.bind_audio_name
    ]

    # 查询不在绑定列表中的音频
    query = RoleAudio.select()

    # 如果有绑定的音频，排除它们
    if bound_audio_names:
        # 使用 ~ 表示NOT，~fn.IN表示不在列表中
        from peewee import fn
        query = query.where(~(RoleAudio.role_name.in_(bound_audio_names)))

    query = query.order_by(RoleAudio.create_time.desc())

    return list(query)


@app.post("/api/novels/upload-batch")
def upload_novels_batch(files: List[UploadFile]):
    """批量上传小说文本文件

    接收多个txt文件，循环打印文件名和内容
    此处添加后续处理逻辑
    """
    results = []

    for file in files:
        try:
            # 获取文件名
            filename = file.filename

            # 读取文件内容
            content = file.file.read()

            # 解码为文本（尝试UTF-8，如果失败则尝试GBK）
            try:
                text_content = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text_content = content.decode('gbk')
                except UnicodeDecodeError:
                    text_content = content.decode('utf-8', errors='ignore')

            # 按行分割
            content_list = text_content.split('\n')

            # 打印文件名和内容信息
            print(f"文件名: {filename}")
            log(f"文件名: {filename}")
            print(f"内容长度: {len(text_content)} 字符")
            log(f"内容长度: {len(text_content)} 字符")
            print("-" * 50)
            log("-" * 50)

            # 提取小说名（去掉.txt扩展名）
            novel_name = filename.replace(".txt", "")

            # 调用split_novel_text_by_content_list函数处理上传的文件
            split_novel_text_by_content_list(content_list, novel_name)

            results.append({
                "filename": filename,
                "content_length": len(text_content),
                "status": "success"
            })
        except Exception as e:
            print(f"处理文件 {filename} 时出错: {str(e)}")
            log(f"处理文件 {filename} 时出错: {str(e)}")
            log_error(f"处理文件 {filename} 时出错: {str(e)}")
            traceback.print_exc()
            results.append({
                "filename": filename,
                "status": "error",
                "error": str(e)
            })

    return {
        "message": f"成功接收 {len(files)} 个文件",
        "files": results
    }


@app.post("/api/role-audios/refresh-batch")
def refresh_role_audios_batch():
    """批量刷新角色音频

    此处添加后续处理逻辑
    用于重新扫描音频文件夹、更新数据库等操作
    """
    # 修改这里：添加后续处理逻辑
    # 例如：
    # - 扫描音频文件夹
    # - 更新音频引用计数
    # - 清理无效的音频记录
    # - 等等...
    update_audio_role()
    return {
        "message": "批量刷新角色音频功能已触发",
        "status": "success"
    }


# ============ WebSocket连接管理 ============
import asyncio

class ConnectionManager:
    """WebSocket连接管理器"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_message(self, message: str):
        """发送消息到所有连接的客户端"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"发送消息失败: {e}")
                log(f"发送消息失败: {e}")
                log_error(f"发送消息失败: {str(e)}")
                disconnected.append(connection)

        # 清理断开的连接
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()


@app.websocket("/ws/logs")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket端点，用于实时传输日志，支持心跳保持连接"""
    await manager.connect(websocket)
    try:
        while True:
            try:
                # 使用超时机制，定期发送心跳
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0  # 30秒超时
                )
                if data == "ping":
                    await websocket.send_text("pong")
                elif data == "heartbeat":
                    await websocket.send_text("heartbeat_ack")
            except asyncio.TimeoutError:
                # 发送心跳包保持连接
                try:
                    await websocket.send_text("[HEARTBEAT]\n")
                except:
                    break
    except Exception as e:
        print(f"WebSocket连接异常: {e}")
        log(f"WebSocket连接异常: {e}")
        log_error(f"WebSocket连接异常: {str(e)}")
    finally:
        manager.disconnect(websocket)


@app.post("/api/novels/batch-analyze")
async def batch_analyze_novel(novel_name: str, thread_count: int, chapter_count: int):
    """批量解析小说

    参数：
    - novel_name: 小说名称
    - thread_count: 线程数
    - chapter_count: 章节数

    功能：
    1. 接收参数并打印
    2. 实时发送日志到前端
    """
    # 打印接收到的参数
    print(f"=" * 50)
    log(f"=" * 50)
    print(f"开始批量解析小说")
    log(f"开始批量解析小说")
    print(f"小说名称: {novel_name}")
    log(f"小说名称: {novel_name}")
    print(f"线程数: {thread_count}")
    log(f"线程数: {thread_count}")
    print(f"章节数: {chapter_count}")
    log(f"章节数: {chapter_count}")
    print(f"=" * 50)
    log(f"=" * 50)

    # 定义日志回调函数，用于将日志发送到前端
    async def log_to_frontend(message):
        """将日志消息发送到WebSocket前端"""
        try:
            await manager.send_message(message + "\n")
        except Exception as e:
            print(f"发送日志到前端失败: {e}")
            log(f"发送日志到前端失败: {e}")
            log_error(f"发送日志到前端失败: {str(e)}")

    # 调用main函数，传递参数和日志回调
    # main函数现在支持novel_name, chapter_count, thread_count和log_callback参数
    await async_parse_text(
        novel_name=novel_name,
        chapter_count=chapter_count,
        thread_count=thread_count,
        log_callback=log_to_frontend
    )

    print(f"解析完成")
    log(f"解析完成")
    await manager.send_message(f"解析完成\n")

    return {
        "message": "批量解析任务已提交",
        "novel_name": novel_name,
        "thread_count": thread_count,
        "chapter_count": chapter_count,
        "status": "success"
    }


@app.get("/api/novel/names")
def get_novel_names_list():
    """获取所有小说名称列表，用于下拉选择"""
    novels = Novel.select(Novel.novel_name).distinct()
    return [novel.novel_name for novel in novels]
    # return {"novel_names": ""}



# ============ 设置管理 API ============
import os

CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'lively_config.json')


class SettingsRequest(BaseModel):
    """设置请求模型"""
    database_name: Optional[str] = None
    max_section_length: Optional[int] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None
    max_token: Optional[int] = None
    preload_role_count: Optional[int] = None
    bind_audio_presence_rate: Optional[float] = None


def get_default_settings() -> dict:
    """获取默认设置"""
    return {
        "database_name": "novels.db",
        "max_section_length": 3000,
        "api_key": "",
        "base_url": "https://api.openai.com/v1",
        "model_name": "gpt-3.5-turbo",
        "max_token": 2000,
        "preload_role_count": 5,
        "bind_audio_presence_rate": 0.4
    }


@app.get("/api/settings")
def get_settings():
    """获取系统设置"""
    if not os.path.exists(CONFIG_FILE):
        return get_default_settings()

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        log(f"读取配置文件失败: {e}")
        log_error(f"读取配置文件失败: {str(e)}")
        return get_default_settings()


@app.post("/api/settings")
def save_settings(settings: SettingsRequest):
    """保存系统设置"""
    try:
        if not os.path.exists(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)

        settings_dict = settings.dict(exclude_none=True)

        existing_settings = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    existing_settings = json.load(f)
            except Exception as e:
                log_error(f"读取配置文件失败: {str(e)}")
                existing_settings = {}

        existing_settings.update(settings_dict)

        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing_settings, f, ensure_ascii=False, indent=4)

        return {
            "message": "设置保存成功",
            "settings": existing_settings
        }
    except Exception as e:
        log_error(f"保存设置失败: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存设置失败: {str(e)}"
        )

#============== 定时任务管理API ===============
class ScheduledParseJob(BaseModel):
    job_id: str
    cron: str
    novel_name: str
    chapter_count: int
    thread_count: int

class ScheduledGenerateJob(BaseModel):
    job_id: str
    cron: str
    novel_name: str
    chapter_count: int

@app.post("/api/scheduled-tasks/parse")
async def create_scheduled_parse_job(job: ScheduledParseJob):
    """创建定时解析任务"""
    try:
        success = add_parse_job(
            job_id=job.job_id,
            cron=job.cron,
            novel_name=job.novel_name,
            chapter_count=job.chapter_count,
            thread_count=job.thread_count
        )

        if success:
            return {
                "message": "定时解析任务创建成功",
                "job_id": job.job_id,
                "status": "success"
            }
        else:
            return {
                "message": "定时解析任务创建失败",
                "status": "failed"
            }
    except Exception as e:
        log_error(f"创建定时解析任务失败: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建定时任务失败: {str(e)}"
        )

@app.post("/api/scheduled-tasks/generate")
async def create_scheduled_generate_job(job: ScheduledGenerateJob):
    """创建定时生成音频任务"""
    try:
        success = add_generate_job(
            job_id=job.job_id,
            cron=job.cron,
            novel_name=job.novel_name,
            chapter_count=job.chapter_count
        )

        if success:
            return {
                "message": "定时生成任务创建成功",
                "job_id": job.job_id,
                "status": "success"
            }
        else:
            return {
                "message": "定时生成任务创建失败",
                "status": "failed"
            }
    except Exception as e:
        log_error(f"创建定时生成任务失败: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建定时任务失败: {str(e)}"
        )

@app.delete("/api/scheduled-tasks/{job_id}")
async def delete_scheduled_job(job_id: str):
    """删除定时任务"""
    try:
        success = remove_job(job_id)

        if success:
            return {
                "message": "定时任务删除成功",
                "job_id": job_id,
                "status": "success"
            }
        else:
            return {
                "message": "定时任务删除失败",
                "status": "failed"
            }
    except Exception as e:
        log_error(f"删除定时任务失败: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除定时任务失败: {str(e)}"
        )

@app.get("/api/scheduled-tasks")
async def list_scheduled_tasks():
    """获取所有定时任务"""
    try:
        jobs = get_all_jobs()
        return {
            "jobs": jobs,
            "status": "success"
        }
    except Exception as e:
        log_error(f"获取定时任务列表失败: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取定时任务列表失败: {str(e)}"
        )

@app.get("/api/scheduled-tasks/status/parse")
async def get_parse_task_running_status():
    """获取解析任务运行状态"""
    try:
        status = get_parse_task_status()
        return status
    except Exception as e:
        log_error(f"获取解析任务状态失败: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务状态失败: {str(e)}"
        )

@app.get("/api/scheduled-tasks/status/generate")
async def get_generate_task_running_status():
    """获取生成任务运行状态"""
    try:
        status = get_generate_task_status()
        return status
    except Exception as e:
        log_error(f"获取生成任务状态失败: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务状态失败: {str(e)}"
        )

@app.get("/api/scheduled-tasks/details")
async def get_scheduled_tasks_details():
    """获取所有任务的详细信息"""
    try:
        details = get_all_task_details()
        return {
            "tasks": details,
            "status": "success"
        }
    except Exception as e:
        log_error(f"获取所有任务详情失败: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务详情失败: {str(e)}"
        )

@app.get("/api/scheduled-tasks/details/{job_id}")
async def get_scheduled_task_detail(job_id: str):
    """获取指定任务的详细信息"""
    try:
        detail = get_task_details(job_id)
        if detail is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务 {job_id} 不存在"
            )
        return detail
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"获取任务详情失败 (job_id={job_id}): {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务详情失败: {str(e)}"
        )

@app.get("/api/scheduled-tasks/logs")
async def get_scheduled_tasks_logs(limit: int = 100):
    """获取任务执行日志"""
    try:
        logs = get_task_logs(limit)
        return {
            "logs": logs,
            "count": len(logs),
            "status": "success"
        }
    except Exception as e:
        log_error(f"获取任务日志失败: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取日志失败: {str(e)}"
        )

@app.delete("/api/scheduled-tasks/logs")
async def clear_scheduled_tasks_logs():
    """清空任务执行日志"""
    try:
        clear_task_logs()
        return {
            "message": "日志已清空",
            "status": "success"
        }
    except Exception as e:
        log_error(f"清空任务日志失败: {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"清空日志失败: {str(e)}"
        )

@app.get("/api/novel/max-chapters")
async def get_max_chapters(novel_name: str, current_state: int):
    """获取指定小说在指定状态下的最大章节数"""
    try:
        count = Novel.select().where(
            Novel.novel_name == novel_name,
            Novel.current_state == current_state
        ).count()

        return {
            "novel_name": novel_name,
            "current_state": current_state,
            "max_chapters": count
        }
    except Exception as e:
        log_error(f"获取最大章节数失败 (novel_name={novel_name}, current_state={current_state}): {str(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取最大章节数失败: {str(e)}"
        )
#============== 定时任务管理API结束 ===============

#============== 前端静态页面 =============== #移动这里
# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 挂载静态文件目录
app.mount("/assets", StaticFiles(directory="admin/dist/assets"), name="assets") #移动这里
# 挂载音频文件目录（支持 WSL 和 Windows）
app.mount("/audios", StaticFiles(directory="audios"), name="audios") #移动这里

# 默认首页路由
@app.get("/") #移动这里
async def serve_index(): #移动这里
    return FileResponse("admin/dist/index.html") #移动这里

# SPA fallback 路由 - 处理 Vue Router 的所有路由
@app.get("/{path:path}") #移动这里
async def serve_spa(path: str): #移动这里
    import os #移动这里
    # 排除 API、assets 和 audios 路由 #移动这里
    if path.startswith('api/') or path.startswith('assets/') or path.startswith('audios/'): #移动这里
        raise HTTPException(status_code=404, detail="Not found") #移动这里

    # 如果是静态文件，直接返回 #移动这里
    file_path = f"admin/dist/{path}" #移动这里
    if os.path.exists(file_path) and os.path.isfile(file_path): #移动这里
        return FileResponse(file_path) #移动这里

    # 对于其他路径，返回 index.html 让 Vue Router 处理 #移动这里
    return FileResponse("admin/dist/index.html") #移动这里
#============== 前端静态页面结束 =============== #移动这里

if __name__ == '__main__':
    import uvicorn

    if __name__ == "__main__":
        uvicorn.run(
            "api:app",
            host="127.0.0.1",
            port=6888,
            reload=True,
            log_level="info"
        )
