import os
from pathlib import Path

from peewee import fn

from bean.beans import RoleAudio, Role
from utils.config import load_config
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

# ============ 全局日志系统 ============
# 线程安全的日志队列
log_queue = queue.Queue()
log_callback_global = None

def log(message):
    """日志输出函数，同时打印和发送到队列"""
    print(message)
    log_queue.put(message)

async def process_log_queue_task():
    """异步处理日志队列"""
    while True:
        try:
            message = log_queue.get(timeout=0.1)
            if log_callback_global:
                await log_callback_global(message)
        except queue.Empty:
            if log_queue.empty():
                await asyncio.sleep(0.1)
        except Exception as e:
            print(f"日志处理错误: {e}")

# ============ 配置管理 ============
class Config:
    """配置管理类"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.config_data = {}

        if config_path and os.path.exists(config_path):
            self.load_from_file(config_path)

    def load_from_file(self, config_path: str):
        """从文件加载配置"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config_data = json.load(f)

    def get(self, key: str, default=None):
        """获取配置项"""
        # 优先从环境变量获取
        env_key = key.upper()
        if os.getenv(env_key):
            return os.getenv(env_key)

        # 从配置文件获取
        keys = key.split('.')
        value = self.config_data
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value if value is not None else default


# ============ 配置示例文件 ============
"""
config.json 示例:
{
    "api_key": "sk-ant-api03-xxx",
    "base_url": "https://api.anthropic.com",
    "model_name": "claude-3-5-sonnet-20241022",
    "max_concurrent_requests": 5,
    "timeout": 120
}
"""


# ============ 动态并发处理器 ============


# ============ 动态并发处理器（修改版） ============
class DynamicConcurrentProcessor:
    """
    使用 Anthropic SDK 的动态并发处理器
    - 始终保持固定数量的并发请求
    - 一个请求完成，立即启动下一个
    - 自动管理任务队列
    - 使用线程池处理流式请求
    """

    def __init__(self, config: Config):
        self.config = config

        # 初始化 Anthropic 客户端
        self.client = anthropic.Anthropic(
            api_key=config.get("api_key"),
            base_url=config.get("base_url", "https://api.anthropic.com")
        )

        # 获取配置参数
        self.model_name = config.get("model_name")
        self.max_concurrent_requests = int(config.get("max_concurrent_requests", 5))
        self.timeout = int(config.get("timeout", 120))

        # 创建线程池用于执行同步的流式请求
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_concurrent_requests * 2
        )

        # 任务队列
        self.task_queue = asyncio.Queue()  # 待处理的任务
        self.result_queue = asyncio.Queue()  # 处理结果

        # 统计信息
        self.stats = {
            'total': 0,
            'completed': 0,
            'failed': 0,
            'start_time': None,
            'end_time': None
        }

        # 回调函数
        self.on_progress_callback = None

    async def send_request(self, task_id: int, text: str, db_id: int = None) -> Dict:
        """
        发送单个请求到 Anthropic API
        使用线程池执行流式请求，避免阻塞事件循环
        """

        def sync_stream_request():
            """同步的流式请求函数"""
            full_response_text = ""
            try:
                with self.client.messages.stream(
                        model=self.model_name,
                        max_tokens=20480,
                        messages=[
                            {
                                "role": "user",
                                "content": text
                            }
                        ],
                        system="你是一位小说信息识别请，请解析我发给你的规则和json文本，只需要将json结果返回给我即可，请注意，你只需要发送纯粹的json字符串即可，不需要md格式的，我需要配合程序解析,请不用返回你思考的内容或关闭思考模式，我想提升速度",
                        thinking={"type": "disabled"}
                ) as stream:
                    for chunk in stream.text_stream:
                        full_response_text += chunk
                return full_response_text
            except Exception as e:
                raise e

        try:
            # 在线程池中执行同步请求
            loop = asyncio.get_event_loop()
            full_response_text = await loop.run_in_executor(
                self.thread_pool,
                sync_stream_request
            )

            return {
                'task_id': task_id,
                'db_id': db_id,  # 添加数据库ID
                'status': 'success',
                'content': full_response_text,
                'raw_response': {
                    'id': None,
                    'model': self.model_name,
                    'stop_reason': None,
                    'usage': {
                        'input_tokens': None,
                        'output_tokens': None
                    }
                },
                'timestamp': time.time()
            }

        except Exception as e:
            traceback.print_exc()
            return {
                'task_id': task_id,
                'db_id': db_id,  # 添加数据库ID
                'status': 'error',
                'error': str(e),
                'timestamp': time.time()
            }

    async def worker(self, worker_id: int):
        """
        工作协程
        从队列中持续获取任务并处理，直到队列为空
        """
        while True:
            try:
                # 从队列获取任务（阻塞直到有任务）
                task = await self.task_queue.get()

                # 检查结束信号
                if task is None:
                    self.task_queue.task_done()
                    break

                task_id = task['id']
                text = task['text']
                db_id = task.get('db_id')  # 获取数据库ID

                log(
                    f"[Worker-{worker_id}] 开始处理任务 {task_id} (数据库ID: {db_id}, 剩余队列: {self.task_queue.qsize()})")

                # 发送请求
                result = await self.send_request(task_id, text, db_id)

                # 更新统计
                if result['status'] == 'success':
                    self.stats['completed'] += 1
                    log(
                        f"[Worker-{worker_id}] ✓ 任务 {task_id} (数据库ID: {db_id}) 完成 ({self.stats['completed']}/{self.stats['total']})")
                else:
                    self.stats['failed'] += 1
                    log(
                        f"[Worker-{worker_id}] ✗ 任务 {task_id} (数据库ID: {db_id}) 失败: {result.get('error')} ({self.stats['failed']}/{self.stats['total']})")

                # 将结果放入结果队列
                await self.result_queue.put(result)

                # 触发进度回调
                if self.on_progress_callback:
                    processed = self.stats['completed'] + self.stats['failed']
                    await self.on_progress_callback(processed, self.stats['total'])

                # 标记任务完成
                self.task_queue.task_done()

            except Exception as e:
                log(f"[Worker-{worker_id}] 异常: {e}")
                traceback.print_exc()
                self.task_queue.task_done()

    async def result_collector(self, results: List[Dict]):
        """结果收集器"""
        collected = 0
        total_expected = self.stats['total']

        while collected < total_expected:
            result = await self.result_queue.get()
            results.append(result)
            collected += 1
            self.result_queue.task_done()

    async def process(self, texts_with_ids: List[tuple], on_progress: Optional[Callable] = None) -> List[Dict]:
        """
        处理文本列表

        Args:
            texts_with_ids: 包含 (text, db_id) 元组的列表，例如 [(text1, id1), (text2, id2), ...]
            on_progress: 进度回调函数 async def on_progress(processed, total)

        Returns:
            处理结果列表
        """
        # 初始化
        self.stats = {
            'total': len(texts_with_ids),
            'completed': 0,
            'failed': 0,
            'start_time': time.time(),
            'end_time': None
        }
        self.on_progress_callback = on_progress

        log(f"\n{'=' * 60}")
        log(f"开始处理 {len(texts_with_ids)} 个文本")
        log(f"并发数: {self.max_concurrent_requests}")
        log(f"线程池大小: {self.max_concurrent_requests * 2}")
        log(f"模型: {self.model_name}")
        log(f"{'=' * 60}\n")

        start_time = time.time()

        # 1. 将所有任务放入队列
        for i, (text, db_id) in enumerate(texts_with_ids):
            await self.task_queue.put({
                'id': i,
                'text': text,
                'db_id': db_id
            })

        # 2. 创建工作池（固定数量的worker）
        workers = []
        for i in range(self.max_concurrent_requests):
            worker_task = asyncio.create_task(self.worker(i))
            workers.append(worker_task)

        # 3. 收集结果
        results = []
        collector_task = asyncio.create_task(self.result_collector(results))

        # 4. 等待所有任务完成
        await self.task_queue.join()

        # 5. 发送结束信号给所有worker
        for _ in range(self.max_concurrent_requests):
            await self.task_queue.put(None)

        # 6. 等待所有worker结束
        await asyncio.gather(*workers)

        # 7. 等待结果收集完成
        await collector_task

        # 统计信息
        self.stats['end_time'] = time.time()
        elapsed = self.stats['end_time'] - start_time

        log(f"\n{'=' * 60}")
        log(f"处理完成！")
        log(f"总任务数: {self.stats['total']}")
        log(f"成功: {self.stats['completed']}")
        log(f"失败: {self.stats['failed']}")
        log(f"总耗时: {elapsed:.2f} 秒")
        log(f"平均每个任务: {elapsed / self.stats['total']:.2f} 秒")
        log(f"吞吐量: {self.stats['total'] / elapsed:.2f} 任务/秒")
        log(f"{'=' * 60}\n")

        return results

    def __del__(self):
        """析构函数，确保线程池被关闭"""
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=False)


# ============ 带解析功能的处理器（修改版） ============
class DynamicConcurrentProcessorWithParser(DynamicConcurrentProcessor):
    """
    带解析功能的动态并发处理器
    - 保持固定并发请求
    - 支持自定义解析逻辑，解析函数接收 (result, db_id) 参数
    """

    def __init__(self, config: Config, parser_func: Optional[Callable] = None):
        super().__init__(config)
        self.parser_func = parser_func

    async def parse_result(self, result: Dict) -> Dict:
        """解析结果"""
        if result['status'] == 'success' and self.parser_func:
            try:
                # 在线程池中执行解析（避免阻塞事件循环）
                # 传入 result 和 db_id
                loop = asyncio.get_event_loop()
                parsed = await loop.run_in_executor(
                    None,
                    self.parser_func,
                    result,  # 传入完整的 result
                    result.get('db_id')  # 传入数据库ID
                )
                result['parsed'] = parsed
            except Exception as e:
                result['parse_error'] = str(e)
                traceback.print_exc()
        return result

    async def result_collector_with_parse(self, results: List[Dict]):
        """带解析的结果收集器"""
        collected = 0
        total_expected = self.stats['total']

        while collected < total_expected:
            result = await self.result_queue.get()
            # 解析结果
            result = await self.parse_result(result)
            results.append(result)

            collected += 1
            self.result_queue.task_done()

    async def process(self, texts_with_ids: List[tuple], on_progress: Optional[Callable] = None) -> List[Dict]:
        """重写process方法，使用带解析的结果收集器"""
        # 初始化
        self.stats = {
            'total': len(texts_with_ids),
            'completed': 0,
            'failed': 0,
            'start_time': time.time(),
            'end_time': None
        }
        self.on_progress_callback = on_progress

        log(f"\n{'=' * 60}")
        log(f"开始处理 {len(texts_with_ids)} 个文本")
        log(f"并发数: {self.max_concurrent_requests}")
        log(f"模型: {self.model_name}")
        log(f"{'=' * 60}\n")

        start_time = time.time()

        # 1. 将所有任务放入队列
        for i, (text, db_id) in enumerate(texts_with_ids):
            await self.task_queue.put({
                'id': i,
                'text': text,
                'db_id': db_id
            })

        # 2. 创建工作池
        workers = []
        for i in range(self.max_concurrent_requests):
            worker_task = asyncio.create_task(self.worker(i))
            workers.append(worker_task)

        # 3. 收集结果（带解析）
        results = []
        collector_task = asyncio.create_task(self.result_collector_with_parse(results))

        # 4. 等待所有任务完成
        await self.task_queue.join()

        # 5. 发送结束信号
        for _ in range(self.max_concurrent_requests):
            await self.task_queue.put(None)

        # 6. 等待所有worker结束
        await asyncio.gather(*workers)

        # 7. 等待结果收集完成
        await collector_task

        # 统计
        self.stats['end_time'] = time.time()
        elapsed = self.stats['end_time'] - start_time

        log(f"\n{'=' * 60}")
        log(f"处理完成！")
        log(f"总任务数: {self.stats['total']}")
        log(f"成功: {self.stats['completed']}")
        log(f"失败: {self.stats['failed']}")
        log(f"总耗时: {elapsed:.2f} 秒")
        log(f"{'=' * 60}\n")

        return results

async def async_parse_text(novel_name=None, chapter_count=None, thread_count=None, log_callback=None):
    """
    修改后的main函数，支持自定义日志输出

    Args:
        novel_name: 小说名称，如果为None则使用默认值"沧元图"
        chapter_count: 章节数量限制，如果为None则使用默认值30
        thread_count: 线程数，如果为None则使用默认值10
        log_callback: 日志回调函数，接收字符串参数，用于将日志发送到前端
    """
    global log_callback_global
    log_callback_global = log_callback

    # 清空之前的日志
    while not log_queue.empty():
        try:
            log_queue.get_nowait()
        except:
            break

    # 启动日志处理任务
    log_task = asyncio.create_task(process_log_queue_task())

    config = Config()
    # 使用传入的线程数或默认值10
    actual_thread_count = thread_count if thread_count else 10

    config.config_data = {
        "api_key": load_config(config_path,"api_key"),
        "base_url": load_config(config_path,"base_url"),
        "model_name": load_config(config_path,"model_name"),
        "max_concurrent_requests": actual_thread_count,  # 使用传入的线程数
    }

    # 使用传入的参数或默认值
    novel_name = novel_name if novel_name else "沧元图"
    chapter_count = chapter_count if chapter_count else 30

    log(f"\n{'=' * 60}")
    log(f"开始处理小说: {novel_name}")
    log(f"最大章节数: {chapter_count}")
    log(f"并发数: {actual_thread_count}")
    log(f"模型: {config.config_data['model_name']}")
    log(f"{'=' * 60}\n")

    # 使用传入的参数或默认值
    novel_name = novel_name if novel_name else "沧元图"
    chapter_count = chapter_count if chapter_count else 30

    log(f"\n{'=' * 60}")
    log(f"开始处理小说: {novel_name}")
    log(f"最大章节数: {chapter_count}")
    log(f"并发数: {config.config_data['max_concurrent_requests']}")
    log(f"模型: {config.config_data['model_name']}")
    log(f"{'=' * 60}\n")

    # 准备数据：创建 (text, db_id) 的列表
    texts_with_ids = []
    # TODO 这里需要修改成按照传进来的小说名字和分析数量进行运行
    # 查询需要处理的章节
    novel_list = Novel.select().where(
        (Novel.novel_name == novel_name) &
        (Novel.current_state == 1)
    ).limit(chapter_count)

    log(f"找到 {len(novel_list)} 个待处理的章节")

    with open("./asset/prompt.txt", "r", encoding="utf-8") as file:
        prompt_text = file.read()

    # 为每个章节创建 (text, db_id) 元组
    for novel in novel_list:
        text = prompt_text + novel.section_data_json
        texts_with_ids.append((text, novel.id))  # novel.id 是数据库主键

    # 定义解析函数，接收 result 和 db_id
    def custom_parser(result, db_id):
        """自定义解析函数，可以访问数据库ID"""
        content = result.get('content')

        try:
            get_db().begin()
            # 根据 db_id 查询对应的数据库记录
            novel = Novel.get_by_id(db_id)

            # 解析JSON内容
            # 清理可能的markdown标记
            content = content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            parse_text_json = json.loads(content)
                # 查询最大章节次数
            role_chapter_max = Role.select().where(
                Role.novel_name == novel.novel_name
            ).order_by(Role.create_time.asc()).first()

            if not role_chapter_max:
                role_chapter_max_count = 0
            else:
                role_chapter_max_count = role_chapter_max.chapter_count

            log(f"处理章节ID: {db_id}")
            log(f"当前最大章节次数: {role_chapter_max_count}")

            # 遍历获取到的所有角色，将新的角色数据添加到旧的角色数据里
            for role in parse_text_json.get("roleList"):
                # 更新旧的角色数据信息
                old_role = Role.get_or_none(
                    (Role.role_name == role["roleName"]) &
                    (Role.novel_name == novel.novel_name)
                )
                gender = role.get("gender")



                if gender != "男":
                    gender = "女"
                # 如果角色信息不存在，则添加新的角色信息
                if not old_role:
                    temp_role = Role.create(
                        role_name=role["roleName"],
                        novel_name=novel.novel_name,
                        role_count=role.get("count"),
                        gender=gender,
                        is_bind=False,
                        bind_audio_name="",
                        chapter_count=role_chapter_max_count + 1,
                        presence_rate = role.get("count") / 1
                    )
                    log(f"添加新角色: {role['roleName']}, 章节次数: {temp_role.chapter_count}")
                else:
                    # 如果角色存在，则更新角色信息
                    presence_rate = (old_role.role_count + role.get("count"))/(role_chapter_max_count + 1)
                    old_role.role_count = old_role.role_count + role.get("count")
                    old_role.chapter_count = role_chapter_max_count + 1
                    old_role.save()
                    log(f"更新角色: {role['roleName']}, 新出现次数: {old_role.role_count}")

            # 更新角色章节数最大值
            role_chapter_max.chapter_count = role_chapter_max_count + 1
            role_chapter_max.save()
            #更新角色具体的出场率
            role_list = Role.select().where(Role.novel_name == novel.novel_name)
            for new_role in role_list:
                new_role.chapter_count = role_chapter_max_count + 1
                new_role.presence_rate = new_role.role_count / (role_chapter_max_count + 1)
                new_role.save()
            # 保存解析后的章节文本
            novel.after_analysis_data_json = json.dumps(
                parse_text_json.get("sentenceList"),
                ensure_ascii=False
            )
            novel.current_state = 2
            novel.save()

            log(f"章节 {db_id} 处理完成")
            get_db().commit()
        except Exception as e:
            log(f"处理章节 {db_id} 时出错: {e}")
            get_db().rollback()
            traceback.print_exc()
            return {
                'error': str(e),
                'success': False
            }

        # 返回解析结果
        return {
            'success': True,
            'length': len(content),
            'word_count': len(content.split()),
            'role_count': len(parse_text_json.get("roleList", [])),
            'sentence_count': len(parse_text_json.get("sentenceList", []))
        }

    # 创建带解析的处理器
    processor_with_parse = DynamicConcurrentProcessorWithParser(config, parser_func=custom_parser)

    # 处理文本（传入 (text, db_id) 列表）
    results_with_parse = await processor_with_parse.process(texts_with_ids)

    # 查看结果
    for result in results_with_parse:
        if result['status'] == 'success':
            log(f"\n任务 {result['task_id']} (数据库ID: {result['db_id']}) 解析完成")
        else:
            log(f"\n任务 {result['task_id']} (数据库ID: {result['db_id']}) 失败: {result.get('error')}")

    # 处理剩余的日志
    await asyncio.sleep(0.5)  # 等待日志队列中的消息被处理
    while not log_queue.empty():
        try:
            message = log_queue.get_nowait()
            if log_callback_global:
                await log_callback_global(message)
        except queue.Empty:
            break

    # 取消日志处理任务
    log_task.cancel()
    try:
        await log_task
    except asyncio.CancelledError:
        pass

def parse_novel_data_bind_role_audio(text_json,parse_text_json,novel_name):
    """
    根据分片数据和解析后的数据制造成等待生成的章节数据，如果没有绑定角色，则自动绑定角色
    :param text_json: 分片的数据
    :param parse_text_json: 解析后的章节数据
    :return:
    """
    text_json_list = json.loads(text_json)
    parse_text_json_list = json.loads(parse_text_json)
    #小说对应数据的列表
    novel_data_list = []
    #查询绑定了角色音频的小说角色
    has_bind_audio_role_name_list = Role.select(Role.bind_audio_name).where(
        (Role.novel_name == novel_name)&
        (Role.bind_audio_name != '')
    )
    has_bind_audio_role_names = []
    for role in has_bind_audio_role_name_list:
        # print(role.bind_audio_name)
        has_bind_audio_role_names.append(role.bind_audio_name)
    #为对应的句子绑定角色音频和类型数据
    for i in range(0,len(text_json_list)):
        for parse_text_json in parse_text_json_list:
            #如果句子跟解析文本对应上
            if i == parse_text_json.get("number"):
                role_name = parse_text_json.get("roleName")
                gender = parse_text_json.get("gender")
                _type = parse_text_json.get("identity")
                if gender != "男":
                    gender = "女"
                bind_audio_name = ""
                if _type == "role":
                    # print(f"类型：{_type}，角色名：{role_name}，章节名：{text_json_list[0]['0']}")
                    role = Role.get_or_none(
                        (Role.role_name == role_name) &
                        (Role.novel_name == novel_name)
                    )
                    # 如果大模型解析语句出现类型为ROLE，但role_name等于空的情况
                    if role is None:
                        role = Role(
                            role_name="BUG角色",
                            novel_name=novel_name,
                            gender=gender,
                            type=_type,
                            bind_audio_name="",
                            role_count = 0,
                            is_bind = False,
                            chapter_count = 0,
                            presence_rate = 0
                        )
                    #小说角色没有绑定角色音频
                    if role.bind_audio_name == "":
                        #查找没有绑定过和符合性别的音频角色
                        not_bind_role_audio_list = RoleAudio.select().where(RoleAudio.role_name.not_in(has_bind_audio_role_names))
                        # print(has_bind_audio_role_names)
                        # print(gender)
                        # print(role.role_name)
                        not_bind_role_audio_list = not_bind_role_audio_list.where(RoleAudio.gender == gender)
                        random_role_audio = not_bind_role_audio_list.order_by(fn.Random()).limit(1)
                        # print(random_role_audio)
                        random_role_audio = random_role_audio.get_or_none()
                        # print("*"*80)
                        #如果还有角色未被绑定
                        if random_role_audio:
                            role.bind_audio_name = random_role_audio.role_name
                            bind_audio_name = random_role_audio.role_name
                        else:
                            #角色已经被绑定完了，从音频库里面随机选一个
                            temp_audio_role = RoleAudio.select().where(RoleAudio.gender == gender).order_by(fn.Random()).limit(1).get_or_none()
                            role.bind_audio_name = temp_audio_role.role_name
                            bind_audio_name = temp_audio_role.role_name
                        #为出场率大于0.3的角色绑定音频
                        if role.role_name != "BUG角色" and role.presence_rate > 0.4:
                            role.bind_audio_name = bind_audio_name
                            role.is_bind = True
                            role.save()
                    elif role.bind_audio_name != "":
                        bind_audio_name = role.bind_audio_name

                #如果小说角色绑定了角色音频
                temp_obj = {
                    "role_name": role_name,
                    "text": text_json_list[i].get(str(i)),
                    "type": _type,
                    "bind_role_audio_name": bind_audio_name
                }
                novel_data_list.append(temp_obj)
                break
    return novel_data_list