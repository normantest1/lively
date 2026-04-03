import sys
import traceback
import datetime
import queue
import os
import glob
import re
from pathlib import Path
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from bean.beans import Novel, ScheduledTask, WatchdogTask, get_db
from nanovllm_voxcpm import VoxCPM
from parse_text import async_parse_text, parse_novel_data_bind_role_audio
from generate_audio import load_role_audio, generate_chapter_audio
from logger import log as logger_log, log_error as logger_log_error
from utils.config import load_config
import asyncio
import concurrent.futures

config_path = Path(__file__).resolve().parent / "config/lively_config.json"

scheduler = AsyncIOScheduler(
    jobstores={'default': MemoryJobStore()},
    job_defaults={
        'coalesce': False,
        'max_instances': 10,
        'misfire_grace_time': 60
    }
)

parse_task_running = False
generate_task_running = False
multithread_generate_task_running = False
watchdog_task_running = False
parse_current_job_id = None
generate_current_job_id = None
multithread_generate_current_job_id = None
watchdog_current_job_id = None
parse_cancel_event = None
generate_cancel_event = None
multithread_generate_cancel_event = None
watchdog_cancel_event = None
server_instance = None
task_logs = {}
task_history = {}

# 批量生成任务状态追踪
batch_generate_state = {
    'threads': 0,           # 线程数
    'total_chapters': 0,    # 总章节数
    'completed_chapters': 0, # 已完成章节数
    'is_paused': False,      # 是否暂停
    'is_stopping': False,    # 是否正在停止
    'needs_batch_execute': False,  # 是否需要执行批量生成（RTF恢复后置为True）
    'batch_executed_since_startup': False,  # 启动后是否已执行过批量生成
    'pending_job_id': '',    # 待执行的job_id
    'pending_novel_name': '', # 待执行的小说名
    'pending_chapter_count': 0,  # 待执行的章节数
    'pending_thread_count': 0    # 待执行的线程数
}

parse_task_lock = asyncio.Lock()
generate_task_lock = asyncio.Lock()
multithread_generate_task_lock = asyncio.Lock()
watchdog_task_lock = asyncio.Lock()

def set_server_instance(server):
    """设置全局server实例"""
    global server_instance
    server_instance = server
    log_info(f"定时任务服务已绑定server实例")

def clear_server_instance():
    """清除全局server实例（停止后调用）"""
    global server_instance
    server_instance = None
    log_info("定时任务服务已解除server实例绑定")

def log_info(message: str):
    """统一的信息日志"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [INFO] {message}"
    print(log_line)
    logger_log(log_line)
    _add_to_logs(log_line)

def log_error(message: str = None):
    """统一的错误日志，包含完整的堆栈跟踪"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if message:
        log_line = f"[{timestamp}] [ERROR] {message}"
        print(log_line)
        logger_log(log_line)
        _add_to_logs(log_line)

    # 获取完整的错误堆栈信息
    exc_type, exc_value, exc_traceback = sys.exc_info()
    if exc_type is not None:
        error_msg = f"[{timestamp}] [ERROR] 完整错误堆栈:\n"
        print(error_msg)
        logger_log(error_msg)
        _add_to_logs(error_msg)

        # 将完整的堆栈跟踪写入日志
        import sys as _sys
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        for line in tb_lines:
            print(line, end='')
            logger_log(line.rstrip())
            _add_to_logs(line.rstrip())

def log_success(message: str):
    """统一的成功日志"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [SUCCESS] {message}"
    print(log_line)
    logger_log(log_line)
    _add_to_logs(log_line)

def log_warning(message: str):
    """统一的警告日志"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [WARNING] {message}"
    print(log_line)
    logger_log(log_line)
    _add_to_logs(log_line)

def _add_to_logs(message: str):
    """内部函数：添加日志到全局日志列表"""
    global task_logs
    if 'global' not in task_logs:
        task_logs['global'] = []
    task_logs['global'].append(message)
    if len(task_logs['global']) > 1000:
        task_logs['global'] = task_logs['global'][-500:]

def get_task_logs(limit: int = 100):
    """获取所有任务日志"""
    global task_logs
    logs = task_logs.get('global', [])
    return logs[-limit:]

def clear_task_logs():
    """清空所有任务日志"""
    global task_logs
    task_logs = {'global': []}
    return True

def parse_cron_field(field: str):
    """解析cron字段，支持 */n 格式"""
    if field.startswith('*/'):
        return f"*/{field[2:]}"
    return field

def is_valid_second(value: str):
    """检查是否为有效的秒字段值"""
    if value == '*':
        return True
    if value.startswith('*/'):
        try:
            return int(value[2:]) > 0
        except:
            return False
    if '-' in value:
        parts = value.split('-')
        return len(parts) == 2 and all(p.strip().isdigit() for p in parts)
    if ',' in value:
        return all(p.strip().isdigit() for p in value.split(','))
    return value.isdigit() and 0 <= int(value) <= 59

def parse_cron(cron: str):
    """解析cron表达式"""
    parts = cron.split()
    if len(parts) == 5:
        minute = parse_cron_field(parts[0])
        hour = parse_cron_field(parts[1])
        day = parse_cron_field(parts[2])
        month = parse_cron_field(parts[3])
        day_of_week = parse_cron_field(parts[4])
        return None, minute, hour, day, month, day_of_week, None
    elif len(parts) == 6:
        if is_valid_second(parts[0]):
            second = parse_cron_field(parts[0])
            minute = parse_cron_field(parts[1])
            hour = parse_cron_field(parts[2])
            day = parse_cron_field(parts[3])
            month = parse_cron_field(parts[4])
            day_of_week = parse_cron_field(parts[5])
            return second, minute, hour, day, month, day_of_week, None
        else:
            minute = parse_cron_field(parts[0])
            hour = parse_cron_field(parts[1])
            day = parse_cron_field(parts[2])
            month = parse_cron_field(parts[3])
            day_of_week = parse_cron_field(parts[4])
            year = parse_cron_field(parts[5])
            return None, minute, hour, day, month, day_of_week, year
    elif len(parts) == 7:
        second = parse_cron_field(parts[0])
        minute = parse_cron_field(parts[1])
        hour = parse_cron_field(parts[2])
        # 处理日字段，确保值在1-31之间
        day = parse_cron_field(parts[3])
        if day == '0':
            day = '*'
        # 处理月字段，确保值在1-12之间
        month = parse_cron_field(parts[4])
        if month == '0':
            month = '*'
        day_of_week = parse_cron_field(parts[5])
        year = parse_cron_field(parts[6])
        return second, minute, hour, day, month, day_of_week, year
    else:
        raise ValueError("Invalid cron format, expected 5-7 fields")

def create_cron_trigger(second, minute, hour, day, month, day_of_week, year):
    """创建CronTrigger，支持可选的秒和年参数"""
    if second is not None and year is not None:
        return CronTrigger(
            second=second,
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            year=year
        )
    elif second is not None:
        return CronTrigger(
            second=second,
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week
        )
    elif year is not None:
        return CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            year=year
        )
    else:
        return CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week
        )

async def execute_parse_task(job_id: str, novel_name: str, chapter_count: int, thread_count: int, log_callback=None):
    """执行批量解析任务
    
    新任务触发时，如果旧任务正在执行，则中断旧任务，立即执行新任务
    """
    global parse_task_running, parse_current_job_id, parse_cancel_event, parse_task_lock

    log_info(f"="*80)
    log_info(f"定时解析任务触发")
    log_info(f"任务ID: {job_id}")
    log_info(f"小说名: {novel_name}")
    log_info(f"章节数: {chapter_count}")
    log_info(f"线程数: {thread_count}")
    log_info(f"="*80)

    if log_callback:
        await log_callback(f"[定时任务] 定时解析任务触发\n")
        await log_callback(f"[定时任务] 任务ID: {job_id}\n")
        await log_callback(f"[定时任务] 小说名: {novel_name}\n")
        await log_callback(f"[定时任务] 章节数: {chapter_count}\n")
        await log_callback(f"[定时任务] 线程数: {thread_count}\n")

    old_task_cancelled = False
    lock_released = False
    await parse_task_lock.acquire()
    try:
        if parse_task_running:
            log_warning(f"发现正在执行的解析任务: {parse_current_job_id}，新任务 {job_id} 将中断旧任务")
            if log_callback:
                await log_callback(f"[警告] 发现正在执行的解析任务: {parse_current_job_id}，新任务将中断旧任务\n")

            if parse_cancel_event:
                parse_cancel_event.set()
                log_info(f"已发送中断信号到任务: {parse_current_job_id}")
                if log_callback:
                    await log_callback(f"[警告] 已发送中断信号到任务: {parse_current_job_id}\n")
                old_task_cancelled = True

        parse_task_running = True
        parse_current_job_id = job_id
        parse_cancel_event = asyncio.Event()
        current_cancel_event = parse_cancel_event

        if old_task_cancelled:
            log_info(f"⏳ 等待旧任务 {parse_current_job_id} 中断完成...")
            if log_callback:
                await log_callback(f"[定时任务] ⏳ 等待旧任务中断完成...\n")
            await asyncio.sleep(0.2)

        # 释放锁
        parse_task_lock.release()
        lock_released = True

    except Exception as e:
        if not lock_released and parse_task_lock.locked():
            parse_task_lock.release()
            lock_released = True
        raise

    try:
        log_info(f"开始执行批量解析任务...")
        if log_callback:
            await log_callback(f"[定时任务] 开始执行批量解析任务\n")

        if current_cancel_event.is_set():
            log_warning(f"任务 {job_id} 被取消（检测到取消信号）")
            if log_callback:
                await log_callback(f"[定时任务] 任务被取消\n")
            return False

        log_info(f"正在查询待解析的小说章节 (current_state=1)...")
        db = get_db()
        if novel_name:
            novels_to_parse = Novel.select().where(
                Novel.novel_name == novel_name,
                Novel.current_state == 1
            ).limit(chapter_count)
        else:
            novels_to_parse = Novel.select().where(
                Novel.current_state == 1
            ).order_by(Novel.create_time.asc()).limit(chapter_count)

        novel_list = list(novels_to_parse)
        total_count = len(novel_list)
        log_info(f"找到 {total_count} 个待解析的章节")

        if log_callback:
            await log_callback(f"[定时任务] 找到 {total_count} 个待解析的章节\n")

        if total_count == 0:
            log_warning(f"没有找到待解析的章节，任务结束")
            if log_callback:
                await log_callback(f"[定时任务] 没有找到待解析的章节\n")
            return True

        log_info(f"开始解析任务，共 {total_count} 个章节")
        if log_callback:
            await log_callback(f"[定时任务] 开始解析任务，共 {total_count} 个章节\n")

        await async_parse_text(
            novel_name=novel_name,
            chapter_count=chapter_count,
            thread_count=thread_count,
            log_callback=log_callback,
            cancel_event=current_cancel_event
        )

        if current_cancel_event.is_set():
            log_warning(f"任务 {job_id} 在执行后被取消")
            if log_callback:
                await log_callback(f"[定时任务] 任务被取消\n")
            return False

        log_success(f"批量解析任务执行完成！共处理 {total_count} 个章节")
        if log_callback:
            await log_callback(f"[定时任务] 批量解析任务执行完成\n")

        return True
    except asyncio.CancelledError:
        log_warning(f"解析任务被取消: {job_id}")
        if log_callback:
            await log_callback(f"[定时任务] 解析任务被取消: {job_id}\n")
        raise
    except Exception as e:
        log_error(f"批量解析任务执行失败: {e}")
        if log_callback:
            await log_callback(f"[定时任务] 批量解析任务执行失败: {e}\n")
        return False
    finally:
        if parse_current_job_id == job_id:
            parse_task_running = False
            parse_current_job_id = None
            parse_cancel_event = None
        log_info(f"解析任务执行器退出，任务ID: {job_id}")

async def execute_generate_task(job_id: str, novel_name: str, chapter_count: int, log_callback=None):
    """执行批量生成音频任务
    
    新任务触发时，如果旧任务正在执行，则中断旧任务，立即执行新任务
    """
    global generate_task_running, generate_current_job_id, generate_cancel_event, server_instance, generate_task_lock

    log_info(f"="*80)
    log_info(f"定时生成音频任务触发")
    log_info(f"任务ID: {job_id}")
    log_info(f"小说名: {novel_name}")
    log_info(f"章节数: {chapter_count}")
    log_info(f"="*80)

    if log_callback:
        await log_callback(f"[定时任务] 定时生成音频任务触发\n")
        await log_callback(f"[定时任务] 任务ID: {job_id}\n")
        await log_callback(f"[定时任务] 小说名: {novel_name}\n")
        await log_callback(f"[定时任务] 章节数: {chapter_count}\n")

    old_task_cancelled = False
    lock_released = False
    await generate_task_lock.acquire()
    try:
        if generate_task_running:
            log_warning(f"发现正在执行的生成任务: {generate_current_job_id}，新任务 {job_id} 将中断旧任务")
            if log_callback:
                await log_callback(f"[警告] 发现正在执行的生成任务: {generate_current_job_id}，新任务将中断旧任务\n")

            if generate_cancel_event:
                generate_cancel_event.set()
                log_info(f"已发送中断信号到任务: {generate_current_job_id}")
                if log_callback:
                    await log_callback(f"[警告] 已发送中断信号到任务: {generate_current_job_id}\n")
                old_task_cancelled = True

        generate_task_running = True
        generate_current_job_id = job_id
        generate_cancel_event = asyncio.Event()
        current_cancel_event = generate_cancel_event

        if old_task_cancelled:
            log_info(f"⏳ 等待旧任务 {generate_current_job_id} 中断完成...")
            if log_callback:
                await log_callback(f"[定时任务] ⏳ 等待旧任务中断完成...\n")
            await asyncio.sleep(0.2)

        # 释放锁
        generate_task_lock.release()
        lock_released = True

    except Exception as e:
        if not lock_released and generate_task_lock.locked():
            generate_task_lock.release()
            lock_released = True
        raise

    try:
        if server_instance is None:
            log_error(f"服务器实例未初始化，无法执行生成任务")
            if log_callback:
                await log_callback(f"[错误] 服务器实例未初始化\n")
            return False

        log_info(f"开始执行批量生成任务...")
        if log_callback:
            await log_callback(f"[定时任务] 开始执行批量生成任务\n")

        if current_cancel_event.is_set():
            log_warning(f"任务 {job_id} 被取消（检测到取消信号）")
            if log_callback:
                await log_callback(f"[定时任务] 任务被取消\n")
            return False

        log_info(f"正在查询待生成的章节 (current_state=2)...")
        db = get_db()
        novels_to_generate = Novel.select().where(
            Novel.novel_name == novel_name,
            Novel.current_state == 2
        ).limit(chapter_count)

        novel_list = list(novels_to_generate)
        total_count = len(novel_list)
        log_info(f"找到 {total_count} 个待生成的章节")

        if log_callback:
            await log_callback(f"[定时任务] 找到 {total_count} 个待生成的章节\n")

        if total_count == 0:
            log_warning(f"没有找到待生成的章节，任务结束")
            if log_callback:
                await log_callback(f"[定时任务] 没有找到待生成的章节\n")
            return True

        log_info(f"正在加载角色音频列表...")
        if log_callback:
            await log_callback(f"[定时任务] 正在加载角色音频列表...\n")

        load_role_list = await load_role_audio(novel_name, server_instance)
        log_info(f"角色音频列表加载完成，共 {len(load_role_list)} 个角色")

        log_info(f"开始生成音频任务，共 {total_count} 个章节")
        if log_callback:
            await log_callback(f"[定时任务] 开始生成音频任务，共 {total_count} 个章节\n")

        success_count = 0
        fail_count = 0

        for idx, novel in enumerate(novel_list, 1):
            if current_cancel_event.is_set():
                log_warning(f"生成任务在执行中被取消: {job_id}，已处理 {idx-1} 个章节")
                if log_callback:
                    await log_callback(f"[定时任务] 生成任务被取消，已处理 {idx-1} 个章节\n")
                return False

            chapter_name = novel.chapter_names if novel.chapter_names else f"章节{novel.id}"
            log_info(f"-"*60)
            log_info(f"正在生成第 {idx}/{total_count} 个章节: {chapter_name}")
            log_info(f"章节ID: {novel.id}")

            if log_callback:
                await log_callback(f"[定时任务] 正在生成第 {idx}/{total_count} 个章节: {chapter_name}\n")

            try:
                chapter_parse_obj_list = parse_novel_data_bind_role_audio(
                    novel.section_data_json,
                    novel.after_analysis_data_json,
                    novel.novel_name
                )

                log_info(f"正在调用TTS生成音频...")

                flag = await generate_chapter_audio(
                    chapter_parse_obj_list,
                    load_role_list,
                    novel_name,
                    novel.id,
                    server_instance
                )

                if flag:
                    log_success(f"✓ 章节 [{chapter_name}] 生成成功")
                    if log_callback:
                        await log_callback(f"[定时任务] ✓ 章节 [{chapter_name}] 生成成功\n")

                    log_info(f"正在更新数据库状态: current_state = 3")
                    novel.current_state = 3
                    novel.save()
                    log_info(f"数据库状态更新完成")

                    success_count += 1
                else:
                    log_error(f"✗ 章节 [{chapter_name}] 生成失败")
                    if log_callback:
                        await log_callback(f"[定时任务] ✗ 章节 [{chapter_name}] 生成失败\n")
                    fail_count += 1

            except Exception as chapter_error:
                log_error(f"✗ 章节 [{chapter_name}] 处理出错: {chapter_error}")
                if log_callback:
                    await log_callback(f"[定时任务] ✗ 章节 [{chapter_name}] 处理出错: {chapter_error}\n")
                fail_count += 1

        if current_cancel_event.is_set():
            log_warning(f"生成任务在完成后被取消: {job_id}")
            if log_callback:
                await log_callback(f"[定时任务] 生成任务被取消\n")
            return False

        log_success(f"="*80)
        log_success(f"批量生成任务执行完成！")
        log_success(f"成功: {success_count} 个章节")
        log_success(f"失败: {fail_count} 个章节")
        log_success(f"="*80)

        if log_callback:
            await log_callback(f"[定时任务] 批量生成任务执行完成\n")
            await log_callback(f"[定时任务] 成功: {success_count} 个章节\n")
            await log_callback(f"[定时任务] 失败: {fail_count} 个章节\n")

        return True
    except asyncio.CancelledError:
        log_warning(f"生成任务被取消: {job_id}")
        if log_callback:
            await log_callback(f"[定时任务] 生成任务被取消: {job_id}\n")
        raise
    except Exception as e:
        log_error(f"批量生成任务执行失败: {e}")
        if log_callback:
            await log_callback(f"[定时任务] 批量生成任务执行失败: {e}\n")
        return False
    finally:
        if generate_current_job_id == job_id:
            generate_task_running = False
            generate_current_job_id = None
            generate_cancel_event = None
        log_info(f"生成任务执行器退出，任务ID: {job_id}")

async def execute_single_chapter_from_queue(thread_id, novel_data, load_role_list, novel_name, server_instance, log_callback=None, cancel_event=None, job_id=None):
    """从队列中执行单个章节的音频生成（在线程中运行）

    参数:
        thread_id: 线程ID
        novel_data: 小说数据
        load_role_list: 加载的角色列表
        novel_name: 小说名
        server_instance: 服务器实例
        log_callback: 日志回调
        cancel_event: 取消事件，用于支持任务取消
        job_id: 任务ID，用于更新看门狗任务记录
    """
    novel = novel_data["novel"]
    chapter_index = novel_data["index"]
    total_chapters = novel_data["total"]
    
    chapter_name = novel.chapter_names if novel.chapter_names else f"章节{novel.id}"
    
    log_info(f"[线程-{thread_id}] 📋 领取任务: 第 {chapter_index}/{total_chapters} 章 - {chapter_name}")
    if log_callback:
        await log_callback(f"[线程-{thread_id}] 📋 领取任务: 第 {chapter_index}/{total_chapters} 章 - {chapter_name}\n")
    
    try:
        # 检查是否被取消
        if cancel_event and cancel_event.is_set():
            log_warning(f"[线程-{thread_id}] ⏹️ 任务被取消（领取时检测），跳过: 第 {chapter_index}/{total_chapters} 章 - {chapter_name}")
            if log_callback:
                await log_callback(f"[线程-{thread_id}] ⏹️ 任务被取消（领取时检测），跳过: 第 {chapter_index}/{total_chapters} 章 - {chapter_name}\n")
            return {
                "success": False, 
                "chapter_index": chapter_index,
                "chapter": chapter_name, 
                "novel_id": novel.id,
                "thread_id": thread_id,
                "cancelled": True
            }
        
        log_info(f"[线程-{thread_id}] ⏳ 开始处理: 第 {chapter_index}/{total_chapters} 章 - {chapter_name}")
        if log_callback:
            await log_callback(f"[线程-{thread_id}] ⏳ 开始处理: 第 {chapter_index}/{total_chapters} 章 - {chapter_name}\n")
        
        chapter_parse_obj_list = parse_novel_data_bind_role_audio(
            novel.section_data_json,
            novel.after_analysis_data_json,
            novel.novel_name
        )
        
        # 再次检查是否被取消
        if cancel_event and cancel_event.is_set():
            log_warning(f"[线程-{thread_id}] ⏹️ 任务被取消（解析后检测），跳过: 第 {chapter_index}/{total_chapters} 章 - {chapter_name}")
            if log_callback:
                await log_callback(f"[线程-{thread_id}] ⏹️ 任务被取消（解析后检测），跳过: 第 {chapter_index}/{total_chapters} 章 - {chapter_name}\n")
            return {
                "success": False, 
                "chapter_index": chapter_index,
                "chapter": chapter_name, 
                "novel_id": novel.id,
                "thread_id": thread_id,
                "cancelled": True
            }
        
        log_info(f"[线程-{thread_id}] 🔊 正在生成音频: 第 {chapter_index}/{total_chapters} 章 - {chapter_name}")
        if log_callback:
            await log_callback(f"[线程-{thread_id}] 🔊 正在生成音频: 第 {chapter_index}/{total_chapters} 章 - {chapter_name}\n")
        
        # 在生成前再次检查取消
        if cancel_event and cancel_event.is_set():
            log_warning(f"[线程-{thread_id}] ⏹️ 任务被取消（生成前检测），跳过: 第 {chapter_index}/{total_chapters} 章 - {chapter_name}")
            if log_callback:
                await log_callback(f"[线程-{thread_id}] ⏹️ 任务被取消（生成前检测），跳过: 第 {chapter_index}/{total_chapters} 章 - {chapter_name}\n")
            return {
                "success": False, 
                "chapter_index": chapter_index,
                "chapter": chapter_name, 
                "novel_id": novel.id,
                "thread_id": thread_id,
                "cancelled": True
            }
        
        log_info(f"[线程-{thread_id}] 🎬 开始调用 generate_chapter_audio，第 {chapter_index}/{total_chapters} 章")
        if log_callback:
            await log_callback(f"[线程-{thread_id}] 🎬 开始调用 generate_chapter_audio，第 {chapter_index}/{total_chapters} 章\n")
        
        flag = await generate_chapter_audio(
            chapter_parse_obj_list,
            load_role_list,
            novel_name,
            novel.id,
            server_instance,
            cancel_event
        )
        
        # 完成后再次检查取消状态
        log_info(f"[线程-{thread_id}] 🎬 generate_chapter_audio 返回: {flag}，检查取消状态")
        if log_callback:
            await log_callback(f"[线程-{thread_id}] 🎬 generate_chapter_audio 返回: {flag}，检查取消状态\n")
        
        if cancel_event and cancel_event.is_set():
            log_warning(f"[线程-{thread_id}] ⏹️ 任务被取消（生成后检测），停止: 第 {chapter_index}/{total_chapters} 章 - {chapter_name}")
            if log_callback:
                await log_callback(f"[线程-{thread_id}] ⏹️ 任务被取消（生成后检测），停止: 第 {chapter_index}/{total_chapters} 章 - {chapter_name}\n")
            return {
                "success": False, 
                "chapter_index": chapter_index,
                "chapter": chapter_name, 
                "novel_id": novel.id,
                "thread_id": thread_id,
                "cancelled": True
            }
        
        if flag:
            log_success(f"[线程-{thread_id}] ✅ 完成: 第 {chapter_index}/{total_chapters} 章 - {chapter_name}")
            if log_callback:
                await log_callback(f"[线程-{thread_id}] ✅ 完成: 第 {chapter_index}/{total_chapters} 章 - {chapter_name}\n")
            
            novel.current_state = 3
            novel.save()

            # 更新已完成章节计数
            if 'completed_chapters' in batch_generate_state:
                batch_generate_state['completed_chapters'] += 1
                remaining = batch_generate_state['total_chapters'] - batch_generate_state['completed_chapters']
                log_info(f"📊 任务进度: {batch_generate_state['completed_chapters']}/{batch_generate_state['total_chapters']} 完成，剩余 {remaining}")
                if log_callback:
                    await log_callback(f"[进度] {batch_generate_state['completed_chapters']}/{batch_generate_state['total_chapters']} 完成，剩余 {remaining}\n")

                # 更新看门狗任务记录
                if job_id:
                    try:
                        db = get_db()
                        with db.atomic():
                            WatchdogTask.update(
                                completed_chapters=batch_generate_state['completed_chapters'],
                                update_time=datetime.datetime.now()
                            ).where(WatchdogTask.job_id == job_id).execute()
                    except Exception as e:
                        log_error(f"更新看门狗任务记录失败: {e}")

            return {
                "success": True, 
                "chapter_index": chapter_index,
                "chapter": chapter_name, 
                "novel_id": novel.id,
                "thread_id": thread_id
            }
        else:
            log_error(f"[线程-{thread_id}] ❌ 失败: 第 {chapter_index}/{total_chapters} 章 - {chapter_name}")
            if log_callback:
                await log_callback(f"[线程-{thread_id}] ❌ 失败: 第 {chapter_index}/{total_chapters} 章 - {chapter_name}\n")
            return {
                "success": False, 
                "chapter_index": chapter_index,
                "chapter": chapter_name, 
                "novel_id": novel.id,
                "thread_id": thread_id
            }
    except Exception as e:
        log_error(f"[线程-{thread_id}] ❌ 出错: 第 {chapter_index}/{total_chapters} 章 - {chapter_name}, 错误: {e}")
        if log_callback:
            await log_callback(f"[线程-{thread_id}] ❌ 出错: 第 {chapter_index}/{total_chapters} 章 - {chapter_name}, 错误: {e}\n")
        return {
            "success": False, 
            "chapter_index": chapter_index,
            "chapter": chapter_name, 
            "error": str(e),
            "thread_id": thread_id
        }

async def execute_multithread_generate_task(job_id: str, novel_name: str, chapter_count: int, thread_count: int, log_callback=None, existing_completed: int = 0):
    """执行多线程批量生成音频任务 - 队列模式

    Args:
        existing_completed: 已完成的章节数（恢复时使用），用于正确累加进度
    """
    global multithread_generate_task_running, multithread_generate_current_job_id, multithread_generate_cancel_event, server_instance, multithread_generate_task_lock

    log_info(f"="*80)
    log_info(f"🎯 定时多线程生成音频任务触发")
    log_info(f"任务ID: {job_id}")
    log_info(f"小说名: {novel_name}")
    log_info(f"总章节数: {chapter_count}")
    log_info(f"线程数: {thread_count}")
    log_info(f"="*80)

    if log_callback:
        await log_callback(f"[定时任务] 🎯 定时多线程生成音频任务触发\n")
        await log_callback(f"[定时任务] 任务ID: {job_id}\n")
        await log_callback(f"[定时任务] 小说名: {novel_name}\n")
        await log_callback(f"[定时任务] 总章节数: {chapter_count}\n")
        await log_callback(f"[定时任务] 线程数: {thread_count}\n")

    old_task_cancelled = False
    old_cancel_event = None
    old_job_id = None
    # 用于 finally 块中判断是否需要释放锁
    lock_released = False

    await multithread_generate_task_lock.acquire()
    try:
        if multithread_generate_task_running:
            old_job_id = multithread_generate_current_job_id
            log_warning(f"⚠️ 发现正在执行的多线程生成任务: {old_job_id}，新任务 {job_id} 将中断旧任务")
            if log_callback:
                await log_callback(f"[警告] 发现正在执行的多线程生成任务: {old_job_id}，新任务将中断旧任务\n")

            # 保存旧任务的取消事件，用于发送取消信号
            old_cancel_event = multithread_generate_cancel_event
            if old_cancel_event:
                old_cancel_event.set()
                log_info(f"已发送中断信号到任务: {old_job_id}")
                if log_callback:
                    await log_callback(f"[警告] 已发送中断信号到任务: {old_job_id}\n")
                old_task_cancelled = True

        # 先等待旧任务完成清理，再修改全局变量
        if old_task_cancelled:
            log_info(f"⏳ 等待旧任务 {old_job_id} 中断完成...")
            if log_callback:
                await log_callback(f"[定时任务] ⏳ 等待旧任务中断完成...\n")
            # 释放锁，让旧任务可以在 finally 中完成清理
            multithread_generate_task_lock.release()
            lock_released = True

            # 等待旧任务完成清理（轮询检查）
            max_wait = 30  # 最多等待30秒
            wait_count = 0
            while multithread_generate_task_running and wait_count < max_wait:
                await asyncio.sleep(1.0)
                wait_count += 1
                log_info(f"⏳ 等待旧任务 {old_job_id} 中断完成... ({wait_count}/{max_wait})")

            if multithread_generate_task_running:
                log_warning(f"⚠️ 旧任务 {old_job_id} 未能在预期时间内完成清理")
            else:
                log_info(f"✅ 旧任务 {old_job_id} 已完成清理")

            # 重新获取锁
            await multithread_generate_task_lock.acquire()
            lock_released = False

        # 创建新的取消事件给新任务使用
        multithread_generate_task_running = True
        multithread_generate_current_job_id = job_id
        multithread_generate_cancel_event = asyncio.Event()
        current_cancel_event = multithread_generate_cancel_event

        # 释放锁
        multithread_generate_task_lock.release()
        lock_released = True

    except Exception as e:
        # 如果发生异常，确保释放锁
        if not lock_released and multithread_generate_task_lock.locked():
            multithread_generate_task_lock.release()
            lock_released = True
        raise

    try:
        log_info(f"🔍 调试：开始执行多线程批量生成任务，server_instance = {server_instance is not None}")
        log_info(f"🔍 调试：multithread_generate_cancel_event = {multithread_generate_cancel_event is not None}, id = {id(multithread_generate_cancel_event) if multithread_generate_cancel_event else 'None'}")
        
        if server_instance is None:
            log_error(f"❌ 服务器实例未初始化，无法执行多线程生成任务")
            if log_callback:
                await log_callback(f"[错误] 服务器实例未初始化\n")
            return False

        log_info(f"🚀 开始执行多线程批量生成任务...")
        if log_callback:
            await log_callback(f"[定时任务] 🚀 开始执行多线程批量生成任务\n")

        # 更新任务状态
        batch_generate_state['threads'] = thread_count
        batch_generate_state['total_chapters'] = chapter_count
        batch_generate_state['completed_chapters'] = existing_completed  # 恢复时使用已完成的章节数
        batch_generate_state['is_paused'] = False
        batch_generate_state['is_stopping'] = False

        log_info(f"🔍 调试：检查取消事件，multithread_generate_cancel_event = {multithread_generate_cancel_event is not None}")
        
        if multithread_generate_cancel_event and multithread_generate_cancel_event.is_set():
            log_warning(f"⚠️ 任务 {job_id} 被取消（检测到取消信号）")
            if log_callback:
                await log_callback(f"[定时任务] 任务被取消\n")
            return False

        log_info(f"📚 正在查询待生成的章节 (current_state=2)...")
        if log_callback:
            await log_callback(f"[定时任务] 📚 正在查询待生成的章节...\n")
            
        db = get_db()
        novels_to_generate = Novel.select().where(
            Novel.novel_name == novel_name,
            Novel.current_state == 2
        ).limit(chapter_count)

        novel_list = list(novels_to_generate)
        total_count = len(novel_list)
        log_info(f"📊 查询结果: 共 {total_count} 个待生成的章节")
        log_info(f"📊 任务配置: 总章节数={chapter_count}, 线程数={thread_count}")

        if log_callback:
            await log_callback(f"[定时任务] 📊 查询结果: 共 {total_count} 个待生成的章节\n")
            await log_callback(f"[定时任务] 📊 任务配置: 总章节数={chapter_count}, 线程数={thread_count}\n")

        if total_count == 0:
            log_warning(f"⚠️ 没有找到待生成的章节，任务结束")
            if log_callback:
                await log_callback(f"[定时任务] 没有找到待生成的章节\n")
            return True

        log_info(f"🎭 正在加载角色音频列表...")
        if log_callback:
            await log_callback(f"[定时任务] 🎭 正在加载角色音频列表...\n")

        load_role_list = await load_role_audio(novel_name, server_instance)
        log_info(f"🎭 角色音频列表加载完成，共 {len(load_role_list)} 个角色")

        log_info(f"="*80)
        log_info(f"🎬 开始多线程生成音频任务")
        log_info(f"   📖 小说名: {novel_name}")
        log_info(f"   📑 总章节数: {total_count}")
        log_info(f"   🧵 线程数: {thread_count}")
        log_info(f"="*80)
        
        if log_callback:
            await log_callback(f"[定时任务] 🎬 开始多线程生成音频任务\n")
            await log_callback(f"[定时任务]    📖 小说名: {novel_name}\n")
            await log_callback(f"[定时任务]    📑 总章节数: {total_count}\n")
            await log_callback(f"[定时任务]    🧵 线程数: {thread_count}\n")

        success_count = 0
        fail_count = 0
        completed_chapters = []
        active_threads = {}

        task_queue = queue.Queue()
        for idx, novel in enumerate(novel_list, 1):
            task_queue.put({
                "novel": novel,
                "index": idx,
                "total": total_count
            })
        
        log_info(f"📋 任务队列初始化完成: {task_queue.qsize()} 个任务进入队列")
        log_info(f"🧵 初始状态: {min(thread_count, total_count)} 个线程开始执行，其余 {max(0, total_count - thread_count)} 个任务等待")
        
        if log_callback:
            await log_callback(f"[定时任务] 📋 任务队列初始化完成: {task_queue.qsize()} 个任务进入队列\n")
            await log_callback(f"[定时任务] 🧵 初始状态: {min(thread_count, total_count)} 个线程开始执行，其余 {max(0, total_count - thread_count)} 个任务等待\n")

        if multithread_generate_cancel_event and multithread_generate_cancel_event.is_set():
            log_warning(f"⚠️ 任务 {job_id} 在队列初始化后被取消")
            return False

        # 检查是否需要暂停
        if batch_generate_state.get('is_paused') or batch_generate_state.get('is_stopping'):
            log_info(f"⏸️ 任务已暂停，等待恢复...")
            if log_callback:
                await log_callback(f"[任务] ⏸️ 任务已暂停，等待恢复...\n")

            # 等待暂停标志清除
            while batch_generate_state.get('is_paused') or batch_generate_state.get('is_stopping'):
                await asyncio.sleep(5)

            log_info(f"▶️ 任务恢复执行")
            if log_callback:
                await log_callback(f"[任务] ▶️ 任务恢复执行\n")

        loop = asyncio.get_event_loop()
        
        task_cancel_event = multithread_generate_cancel_event
        task_job_id = job_id
        
        log_info(f"🔍 调试：为任务 {job_id} 创建独立的cancel_event，event_id = {id(task_cancel_event) if task_cancel_event else 'None'}")

        async def worker_task(thread_id):
            """工作线程任务：从队列获取任务并执行"""
            global server_instance
            nonlocal success_count, fail_count

            log_info(f"[线程-{thread_id}] 🔍 调试：worker_task {task_job_id} 启动，task_cancel_event = {task_cancel_event is not None}, event_id = {id(task_cancel_event) if task_cancel_event else 'None'}")
            
            if task_cancel_event is None:
                log_error(f"[线程-{thread_id}] ❌ 错误：task_cancel_event 为 None")
                return
            
            if task_cancel_event.is_set():
                log_info(f"[线程-{thread_id}] 🟡 检测到取消信号，任务 {task_job_id} 已取消")
                return
            
            log_info(f"[线程-{thread_id}] 🟢 启动，检查取消状态: {task_cancel_event.is_set()}")
            
            while not task_cancel_event.is_set():
                log_info(f"[线程-{thread_id}] 🔵 获取任务前检查: {task_cancel_event.is_set()}")
                
                try:
                    task_data = task_queue.get_nowait()
                except queue.Empty:
                    log_info(f"[线程-{thread_id}] 🔚 队列为空，线程退出")
                    if log_callback:
                        await log_callback(f"[线程-{thread_id}] 🔚 队列为空，线程退出\n")
                    break
                
                log_info(f"[线程-{thread_id}] 🟢 领取任务，检查: {task_cancel_event.is_set()}")
                
                result = await execute_single_chapter_from_queue(
                    thread_id,
                    task_data,
                    load_role_list,
                    novel_name,
                    server_instance,
                    log_callback,
                    task_cancel_event,
                    task_job_id
                )
                
                completed_chapters.append(result)
                if result["success"]:
                    success_count += 1
                else:
                    fail_count += 1
                
                task_queue.task_done()
                
                progress = f"进度: {len(completed_chapters)}/{total_count} ({len(completed_chapters)*100//total_count}%)"
                remaining = task_queue.qsize()
                log_info(f"📈 任务进度更新: {progress}, 剩余待执行: {remaining} 个任务")
                
                if log_callback:
                    await log_callback(f"[定时任务] 📈 任务进度更新: {progress}, 剩余待执行: {remaining} 个任务\n")

                # 每章节完成后检查RTF
                high_rtf = await check_rtf_in_logs(log_callback)
                if high_rtf:
                    rtf_threshold = load_config(config_path, "rtf_threshold") or 0.8
                    log_warning(f"⚠️ 检测到RTF>{rtf_threshold}，准备重启服务器...")
                    if log_callback:
                        await log_callback(f"[看门狗] ⚠️ 检测到RTF>{rtf_threshold}，准备重启服务器\n")
                    # 设置取消事件，通知所有worker停止
                    task_cancel_event.set()
                    # 记录当前状态
                    completed = success_count + fail_count
                    remaining_chapters = total_count - completed
                    log_warning(f"📊 任务中断状态: 线程数={thread_count}, 总章节={total_count}, 已完成={completed}, 剩余={remaining_chapters}")
                    if log_callback:
                        await log_callback(f"[看门狗] 📊 任务中断状态: 线程数={thread_count}, 总章节={total_count}, 已完成={completed}, 剩余={remaining_chapters}\n")
                    # 停止服务器
                    await server_instance.stop()
                    # 从配置读取等待时间
                    reload_wait = load_config(config_path, "watchdog_reload_wait_seconds") or 60
                    resume_wait = load_config(config_path, "watchdog_resume_wait_seconds") or 120
                    # 等待reload_wait秒后重新加载
                    log_info(f"⏳ 等待{reload_wait}秒后重新加载模型...")
                    if log_callback:
                        await log_callback(f"[看门狗] ⏳ 等待{reload_wait}秒后重新加载模型...\n")
                    await asyncio.sleep(reload_wait)
                    log_info("🔄 重新加载VoxCPM模型...")
                    if log_callback:
                        await log_callback("[看门狗] 🔄 重新加载VoxCPM模型...\n")
                    # 重新加载模型
                    server_instance = VoxCPM.from_pretrained(
                        "./VoxCPM1.5/",
                        max_num_batched_tokens=8192,
                        max_num_seqs=16,
                        max_model_len=4096,
                        gpu_memory_utilization=0.95,
                        enforce_eager=False,
                        devices=[0]
                    )
                    set_server_instance(server_instance)
                    # 等待resume_wait秒后恢复任务
                    log_info(f"⏳ 等待{resume_wait}秒后恢复任务...")
                    if log_callback:
                        await log_callback(f"[看门狗] ⏳ 等待{resume_wait}秒后恢复任务...\n")
                    await asyncio.sleep(resume_wait)
                    # 重新查询剩余章节（current_state=2）
                    db = get_db()
                    remaining_novels = Novel.select().where(
                        Novel.novel_name == novel_name,
                        Novel.current_state == 2
                    ).limit(chapter_count)
                    remaining_list = list(remaining_novels)
                    remaining_total = len(remaining_list)
                    log_info(f"🔄 恢复任务，剩余 {remaining_total} 个章节待生成")
                    if log_callback:
                        await log_callback(f"[看门狗] 🔄 恢复任务，剩余 {remaining_total} 个章节待生成\n")
                    # 重新构建队列
                    for novel in remaining_list:
                        task_queue.put({"novel": novel, "index": novel.id, "total": remaining_total})
                    # 重置计数器和已完成列表
                    success_count = 0
                    fail_count = 0
                    completed_chapters.clear()
                    # 创建新的cancel事件和worker
                    resume_cancel_event = asyncio.Event()
                    async def worker_task_resume(tid):
                        nonlocal success_count, fail_count
                        while not resume_cancel_event.is_set():
                            try:
                                task_data = task_queue.get_nowait()
                            except queue.Empty:
                                break
                            result = await execute_single_chapter_from_queue(
                                tid, task_data, load_role_list, novel_name,
                                server_instance, log_callback, resume_cancel_event
                            )
                            completed_chapters.append(result)
                            if result["success"]:
                                success_count += 1
                            else:
                                fail_count += 1
                            task_queue.task_done()
                            # 继续检查RTF（链式检测）
                            next_rtf = await check_rtf_in_logs(log_callback)
                            if next_rtf:
                                rtf_threshold = load_config(config_path, "rtf_threshold") or 0.8
                                log_warning(f"⚠️ 恢复后再次检测到RTF>{rtf_threshold}...")
                                resume_cancel_event.set()
                                break
                    resume_tasks = [loop.create_task(worker_task_resume(i+1)) for i in range(thread_count)]
                    await asyncio.gather(*resume_tasks)
                    # 恢复后的最终统计
                    if log_callback:
                        await log_callback(f"[看门狗] 🔄 恢复任务完成，成功:{success_count} 失败:{fail_count}\n")
                    log_info(f"🔄 恢复任务完成，成功:{success_count} 失败:{fail_count}")
                    return True

        tasks = []
        for i in range(thread_count):
            thread_id = i + 1
            log_info(f"🧵 启动工作线程-{thread_id}")
            if log_callback:
                await log_callback(f"[定时任务] 🧵 启动工作线程-{thread_id}\n")
            tasks.append(loop.create_task(worker_task(thread_id)))
        
        await asyncio.gather(*tasks)
        
        log_info(f"="*80)
        log_info(f"🏁 所有工作线程执行完成")
        log_info(f"📊 执行结果统计:")
        log_info(f"   ✅ 成功: {success_count} 个章节")
        log_info(f"   ❌ 失败: {fail_count} 个章节")
        log_info(f"   📈 总计: {success_count + fail_count} 个章节")
        log_info(f"="*80)

        if log_callback:
            await log_callback(f"[定时任务] 🏁 所有工作线程执行完成\n")
            await log_callback(f"[定时任务] 📊 执行结果统计:\n")
            await log_callback(f"[定时任务]    ✅ 成功: {success_count} 个章节\n")
            await log_callback(f"[定时任务]    ❌ 失败: {fail_count} 个章节\n")
            await log_callback(f"[定时任务]    📈 总计: {success_count + fail_count} 个章节\n")

        return True
    except asyncio.CancelledError:
        log_warning(f"⚠️ 多线程生成任务被取消: {job_id}")
        if log_callback:
            await log_callback(f"[定时任务] ⚠️ 多线程生成任务被取消: {job_id}\n")
        raise
    except Exception as e:
        log_error(f"❌ 多线程批量生成任务执行失败: {e}")
        if log_callback:
            await log_callback(f"[定时任务] ❌ 多线程批量生成任务执行失败: {e}\n")
        return False
    finally:
        if multithread_generate_current_job_id == job_id:
            multithread_generate_task_running = False
            multithread_generate_current_job_id = None
            multithread_generate_cancel_event = None
        log_info(f"🏃 多线程生成任务执行器退出，任务ID: {job_id}")

async def execute_watchdog_task(job_id: str, novel_name: str = '', chapter_count: int = 0, thread_count: int = 0, log_callback=None, is_recovery: bool = False, existing_completed: int = 0):
    """执行看门狗任务

    简化逻辑：
    1. 第一次触发（启动后）：执行批量生成
    2. 第二次及以后触发：跳过批量生成
    3. RTF超标后TTS恢复，下次触发：执行批量生成
    4. 之后的触发：跳过批量生成
    """
    global watchdog_task_running, watchdog_current_job_id, watchdog_cancel_event, server_instance, batch_generate_state

    log_info(f"="*80)
    log_info(f"🐕 看门狗任务触发")
    log_info(f"任务ID: {job_id}")
    log_info(f"小说名: {novel_name}")
    log_info(f"章节数: {chapter_count}")
    log_info(f"线程数: {thread_count}")
    log_info(f"="*80)

    if log_callback:
        await log_callback(f"[看门狗任务] 🐕 定时任务触发\n")
        await log_callback(f"[看门狗任务] 任务ID: {job_id}\n")
        await log_callback(f"[看门狗任务] 小说名: {novel_name}\n")
        await log_callback(f"[看门狗任务] 章节数: {chapter_count}\n")
        await log_callback(f"[看门狗任务] 线程数: {thread_count}\n")

    try:
        # Step 1: 检查RTF
        log_info(f"🔍 开始RTF检测...")
        is_high_rtf = await check_rtf_in_logs(log_callback)

        rtf_handled_this_trigger = False  # 标记本次触发是否处理了RTF

        if is_high_rtf:
            log_warning(f"⚠️ RTF超过阈值，开始处理...")
            if log_callback:
                await log_callback(f"[RTF检测] ⚠️ RTF超过阈值，开始处理...\n")
            # 存储参数到 batch_generate_state，供 handle_high_rtf 恢复后使用
            batch_generate_state['pending_job_id'] = job_id
            batch_generate_state['pending_novel_name'] = novel_name
            batch_generate_state['pending_chapter_count'] = chapter_count
            batch_generate_state['pending_thread_count'] = thread_count
            log_info(f"📌 已存储RTF恢复参数: job_id={job_id}, novel={novel_name}, chapters={chapter_count}, threads={thread_count}")
            # 立即设置 needs_batch=True（同步），确保下次触发能执行
            # 注意：handle_high_rtf 也会设置 needs_batch，但异步执行可能来不及
            batch_generate_state['needs_batch_execute'] = True
            log_info(f"📌 已设置needs_batch=True，批量生成将在下次触发时执行")
            await handle_high_rtf(log_callback)
            rtf_handled_this_trigger = True
        else:
            log_info(f"✅ RTF 检查正常")
            if log_callback:
                await log_callback(f"[RTF检测] ✅ RTF 正常\n")

        # Step 2: 检查 watchdog_auto_recovery 配置
        auto_recovery_enabled = True
        try:
            auto_recovery_enabled = load_config(config_path, "watchdog_auto_recovery")
            if auto_recovery_enabled is None:
                auto_recovery_enabled = True  # 默认开启
        except:
            auto_recovery_enabled = True

        log_info(f"🔍 [配置检查] watchdog_auto_recovery = {auto_recovery_enabled}")

        # Step 3: 决定是否执行批量生成
        # 注意：needs_batch_execute 在 handle_high_rtf 中设置，但批量生成在【下次触发】执行
        # 判断依据：
        # - needs_batch_execute = True (RTF恢复后标记) -> 执行批量生成
        # - batch_executed_since_startup = False (启动后从未执行) AND auto_recovery = True -> 执行批量生成
        # - 否则 -> 跳过批量生成
        # 重要：如果本次触发处理了RTF（handle_high_rtf被调用），则【不执行】批量生成，等待下次触发
        should_execute_batch = False

        # 调试日志
        log_info(f"🔍 [批量执行决策] job_id={job_id}, novel_name={novel_name}, rtf_handled={rtf_handled_this_trigger}, needs_batch={batch_generate_state['needs_batch_execute']}, executed_since_startup={batch_generate_state['batch_executed_since_startup']}, auto_recovery={auto_recovery_enabled}")

        if rtf_handled_this_trigger:
            # RTF恢复后，下次触发才执行批量生成，本次跳过
            # 注意：不消耗 needs_batch，保留到下次触发
            log_info(f"⏭️ RTF已处理，批量生成将在下次触发时执行（needs_batch保持={batch_generate_state['needs_batch_execute']}）")
            if log_callback:
                await log_callback(f"[看门狗] ⏭️ RTF已处理，批量生成将在下次触发时执行\n")
        elif batch_generate_state['needs_batch_execute']:
            # RTF恢复后的下一次触发需要执行批量生成（RTF恢复不依赖auto_recovery开关）
            # 只有参数有效时才执行，否则保留 needs_batch
            if novel_name and chapter_count > 0:
                should_execute_batch = True
                batch_generate_state['needs_batch_execute'] = False
                log_info(f"📌 检测到RTF恢复标记，执行批量生成（needs_batch已消耗）")
            else:
                log_info(f"⏭️ 检测到RTF恢复标记，但参数无效（novel={novel_name}, chapters={chapter_count}），保留needs_batch")
                if log_callback:
                    await log_callback(f"[看门狗] ⏭️ RTF恢复标记已记录，等待有效参数\n")
        elif not batch_generate_state['batch_executed_since_startup'] and auto_recovery_enabled:
            # 启动后第一次触发 AND 自动恢复开启，执行批量生成
            # 只有参数有效时才执行
            if novel_name and chapter_count > 0:
                should_execute_batch = True
                batch_generate_state['batch_executed_since_startup'] = True
                log_info(f"📌 检测到启动后首次触发，执行批量生成")
            else:
                log_info(f"⏭️ 检测到启动后首次触发，但参数无效（novel={novel_name}, chapters={chapter_count}），跳过")
                if log_callback:
                    await log_callback(f"[看门狗] ⏭️ 启动后首次触发参数无效，跳过\n")
        elif auto_recovery_enabled:
            # 自动恢复开启，但已执行过，跳过
            log_info(f"⏭️ 已执行过批量生成，跳过本次执行")
            if log_callback:
                await log_callback(f"[看门狗] ⏭️ 已执行过批量生成，跳过\n")
        else:
            # 自动恢复关闭，跳过批量生成
            log_info(f"⏭️ 自动恢复已关闭，跳过批量生成")
            if log_callback:
                await log_callback(f"[看门狗] ⏭️ 自动恢复已关闭，跳过批量生成\n")

        # Step 3: 执行批量生成（如果需要）
        if should_execute_batch and novel_name and chapter_count > 0:
            log_info(f"🐕 开始执行多线程生成音频任务...")
            if log_callback:
                await log_callback(f"[看门狗任务] 🐕 开始执行多线程生成音频任务...\n")

            await execute_multithread_generate_task(
                job_id=job_id,
                novel_name=novel_name,
                chapter_count=chapter_count,
                thread_count=thread_count,
                log_callback=log_callback,
                existing_completed=0
            )

            log_info(f"🐕 多线程生成音频任务执行完成")
            if log_callback:
                await log_callback(f"[看门狗任务] 🐕 多线程生成音频任务执行完成\n")

        log_info(f"🐕 看门狗任务执行完成")
        if log_callback:
            await log_callback(f"[看门狗任务] 🐕 看门狗任务执行完成\n")

        log_success(f"="*80)
        return True

    except asyncio.CancelledError:
        log_warning(f"⚠️ 看门狗任务被取消: {job_id}")
        if log_callback:
            await log_callback(f"[看门狗任务] ⚠️ 看门狗任务被取消: {job_id}\n")
        raise
    except Exception as e:
        log_error(f"❌ 看门狗任务执行失败: {e}")
        traceback.print_exc()
        if log_callback:
            await log_callback(f"[看门狗任务] ❌ 看门狗任务执行失败: {e}\n")
        return False

async def check_rtf_in_logs(log_callback=None) -> bool:
    """检查日志文件中的RTF值，返回是否发现高RTF (>threshold)"""
    found_high_rtf = False
    try:
        # 从配置读取RTF阈值和日志检查行数
        rtf_threshold = load_config(config_path, "rtf_threshold") or 0.8
        log_check_lines = load_config(config_path, "watchdog_log_check_lines") or 10

        log_dir = "./logs"

        if not os.path.exists(log_dir):
            log_warning(f"⚠️ 日志目录不存在: {log_dir}")
            if log_callback:
                await log_callback(f"[看门狗任务] ⚠️ 日志目录不存在: {log_dir}\n")
            return False

        log_files = glob.glob(os.path.join(log_dir, "*.log"))

        if not log_files:
            log_warning(f"⚠️ 未找到任何日志文件")
            if log_callback:
                await log_callback(f"[看门狗任务] ⚠️ 未找到任何日志文件\n")
            return False

        latest_log_file = max(log_files, key=os.path.getctime)

        log_info(f"📄 检查最新日志文件: {latest_log_file}")
        if log_callback:
            await log_callback(f"[看门狗任务] 📄 检查最新日志文件: {latest_log_file}\n")

        try:
            with open(latest_log_file, 'r', encoding='utf-8') as f:
                all_lines = f.readlines()
        except Exception as e:
            log_error(f"❌ 读取日志文件失败: {e}")
            if log_callback:
                await log_callback(f"[看门狗任务] ❌ 读取日志文件失败: {e}\n")
            return False

        last_n_lines = all_lines[-log_check_lines:] if len(all_lines) >= log_check_lines else all_lines

        log_info(f"📊 检查最后 {len(last_n_lines)} 行日志...")
        if log_callback:
            await log_callback(f"[看门狗任务] 📊 检查最后 {len(last_n_lines)} 行日志...\n")

        rtf_pattern = re.compile(r'RTF[：:]\s*([\d.]+)')
        for line in last_n_lines:
            match = rtf_pattern.search(line)
            if match:
                rtf_value = float(match.group(1))
                line_stripped = line.strip()

                log_info(f"🔍 发现RTF日志: {line_stripped}")
                if log_callback:
                    await log_callback(f"[看门狗任务] 🔍 发现RTF日志: {line_stripped}\n")

                if rtf_value > rtf_threshold:
                    found_high_rtf = True
                    warning_msg = f"⚠️ 发现RTF大于{rtf_threshold}: {rtf_value}"
                    log_warning(warning_msg)
                    if log_callback:
                        await log_callback(f"[看门狗任务] ⚠️ 发现RTF大于{rtf_threshold}: {rtf_value}\n")

                    print(f"\n{'='*80}")
                    print(f"⚠️ 看门狗警告：发现RTF大于{rtf_threshold}")
                    print(f"日志内容: {line_stripped}")
                    print(f"RTF值: {rtf_value}")
                    print(f"{'='*80}\n")
        if found_high_rtf:
            for i in range(0,len(last_n_lines)):
                log_info(f"发现RTF大于{rtf_threshold},为防止TTS模型重启后再次读到旧日志，将日志填充中，行数：{str(i+1)}")
        if not found_high_rtf:
            log_info(f"✅ 未发现RTF大于{rtf_threshold}的日志")
            if log_callback:
                await log_callback(f"[看门狗任务] ✅ 未发现RTF大于{rtf_threshold}的日志\n")

    except Exception as e:
        log_error(f"❌ 检查RTF时出错: {e}")
        if log_callback:
            await log_callback(f"[看门狗任务] ❌ 检查RTF时出错: {e}\n")
        return False

    return found_high_rtf

async def handle_high_rtf(log_callback=None):
    """处理 RTF > threshold 的情况：停止 server、等待、重加载、恢复任务"""
    global server_instance, batch_generate_state

    try:
        # 从配置读取RTF阈值和等待时间
        rtf_threshold = load_config(config_path, "rtf_threshold") or 0.8
        reload_wait = load_config(config_path, "watchdog_reload_wait_seconds") or 60
        resume_wait = load_config(config_path, "watchdog_resume_wait_seconds") or 120

        log_warning(f"{'='*60}")
        log_warning(f"⚠️ 发现RTF大于{rtf_threshold}，开始处理...")
        log_warning(f"{'='*60}")

        if log_callback:
            await log_callback(f"[RTF处理] ⚠️ 发现RTF大于{rtf_threshold}，开始处理...\n")

        # 1. 标记任务为暂停状态
        batch_generate_state['is_paused'] = True
        batch_generate_state['is_stopping'] = True

        # 2. 停止 server
        if server_instance is not None:
            log_info(f"🛑 停止 VoxCPM server...")
            if log_callback:
                await log_callback(f"[RTF处理] 🛑 停止 VoxCPM server...\n")
            await server_instance.stop()
            log_info(f"✅ Server 已停止")
        else:
            log_warning(f"⚠️ server_instance 为 None，跳过停止")

        # 3. 等待 reload_wait 秒
        log_info(f"⏳ 等待 {reload_wait} 秒后重新加载模型...")
        if log_callback:
            await log_callback(f"[RTF处理] ⏳ 等待 {reload_wait} 秒...\n")
        await asyncio.sleep(reload_wait)

        # 4. 重新加载模型
        log_info(f"🔄 重新加载 VoxCPM 模型...")
        if log_callback:
            await log_callback(f"[RTF处理] 🔄 重新加载模型...\n")

        from nanovllm_voxcpm import VoxCPM

        new_server = VoxCPM.from_pretrained(
            "./VoxCPM1.5/",
            max_num_batched_tokens=8192,
            max_num_seqs=16,
            max_model_len=4096,
            gpu_memory_utilization=0.95,
            enforce_eager=False,
            devices=[0]
        )

        # 5. 更新全局 server 实例
        server_instance = new_server
        set_server_instance(new_server)
        log_info(f"✅ 模型重新加载完成")

        if log_callback:
            await log_callback(f"[RTF处理] ✅ 模型重新加载完成\n")

        # 6. 标记停止完成
        batch_generate_state['is_stopping'] = False

        # 7. 等待 resume_wait 秒后恢复任务
        log_info(f"⏳ 等待 {resume_wait} 秒后恢复任务...")
        if log_callback:
            await log_callback(f"[RTF处理] ⏳ 等待 {resume_wait} 秒后恢复任务...\n")
        await asyncio.sleep(resume_wait)

        # 8. 恢复任务
        if batch_generate_state['is_paused']:
            batch_generate_state['is_paused'] = False
            log_info(f"🔄 恢复批量生成任务...")
            if log_callback:
                await log_callback(f"[RTF处理] 🔄 恢复批量生成任务...\n")

        # 9. 使用存储的参数直接执行批量生成
        pending_job_id = batch_generate_state.get('pending_job_id', '')
        pending_novel_name = batch_generate_state.get('pending_novel_name', '')
        pending_chapter_count = batch_generate_state.get('pending_chapter_count', 0)
        pending_thread_count = batch_generate_state.get('pending_thread_count', 0)

        if pending_novel_name and pending_chapter_count > 0:
            log_info(f"📌 RTF恢复后直接执行批量生成: novel={pending_novel_name}, chapters={pending_chapter_count}, threads={pending_thread_count}")
            if log_callback:
                await log_callback(f"[RTF处理] 📌 RTF恢复后直接执行批量生成\n")

            # 直接执行批量生成任务
            await execute_multithread_generate_task(
                job_id=pending_job_id,
                novel_name=pending_novel_name,
                chapter_count=pending_chapter_count,
                thread_count=pending_thread_count,
                log_callback=log_callback,
                existing_completed=0
            )

            log_info(f"📌 RTF恢复后的批量生成任务执行完成")
            if log_callback:
                await log_callback(f"[RTF处理] 📌 RTF恢复后的批量生成任务执行完成\n")

            # 清理存储的参数
            batch_generate_state['pending_job_id'] = ''
            batch_generate_state['pending_novel_name'] = ''
            batch_generate_state['pending_chapter_count'] = 0
            batch_generate_state['pending_thread_count'] = 0
        else:
            # 如果没有存储的参数，标记需要下次触发时执行
            batch_generate_state['needs_batch_execute'] = True
            log_info(f"📌 已标记需要执行批量生成，下次触发将执行")
            if log_callback:
                await log_callback(f"[RTF处理] 📌 已标记需要执行批量生成，下次触发将执行\n")

    except Exception as e:
        log_error(f"❌ 处理 RTF 失败: {e}")
        if log_callback:
            await log_callback(f"[RTF处理] ❌ 处理失败: {e}\n")
        batch_generate_state['is_stopping'] = False

def add_parse_job(job_id: str, cron: str, novel_name: str, chapter_count: int, thread_count: int):
    """添加定时解析任务"""
    try:
        second, minute, hour, day, month, day_of_week, year = parse_cron(cron)

        trigger = create_cron_trigger(second, minute, hour, day, month, day_of_week, year)

        scheduler.add_job(
            execute_parse_task,
            trigger=trigger,
            id=job_id,
            name=f"定时解析任务_{novel_name or '全部'}",
            args=[job_id, novel_name, chapter_count, thread_count],
            replace_existing=True
        )

        db = get_db()
        task, created = ScheduledTask.get_or_create(
            job_id=job_id,
            defaults={
                'job_type': 'parse',
                'cron': cron,
                'novel_name': novel_name,
                'chapter_count': chapter_count,
                'thread_count': thread_count,
                'is_active': True,
                'update_time': datetime.datetime.now()
            }
        )

        if not created:
            task.job_type = 'parse'
            task.cron = cron
            task.novel_name = novel_name
            task.chapter_count = chapter_count
            task.thread_count = thread_count
            task.is_active = True
            task.update_time = datetime.datetime.now()
            task.save()

        job = scheduler.get_job(job_id)
        next_run = job.next_run_time if job else None
        next_run_str = next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else "N/A"

        log_success(f"添加解析任务成功: {job_id}")
        log_info(f"  - 小说名: {novel_name}")
        log_info(f"  - Cron: {cron}")
        log_info(f"  - 章节数: {chapter_count}")
        log_info(f"  - 线程数: {thread_count}")
        log_info(f"  - 下次执行时间: {next_run_str}")
        return True
    except Exception as e:
        log_error(f"添加解析任务失败: {e}")
        return False

def add_generate_job(job_id: str, cron: str, novel_name: str, chapter_count: int):
    """添加定时生成音频任务"""
    try:
        second, minute, hour, day, month, day_of_week, year = parse_cron(cron)

        trigger = create_cron_trigger(second, minute, hour, day, month, day_of_week, year)

        scheduler.add_job(
            execute_generate_task,
            trigger=trigger,
            id=job_id,
            name=f"定时生成任务_{novel_name}",
            args=[job_id, novel_name, chapter_count],
            replace_existing=True
        )

        db = get_db()
        task, created = ScheduledTask.get_or_create(
            job_id=job_id,
            defaults={
                'job_type': 'generate',
                'cron': cron,
                'novel_name': novel_name,
                'chapter_count': chapter_count,
                'thread_count': 1,
                'is_active': True,
                'update_time': datetime.datetime.now()
            }
        )

        if not created:
            task.job_type = 'generate'
            task.cron = cron
            task.novel_name = novel_name
            task.chapter_count = chapter_count
            task.thread_count = 1
            task.is_active = True
            task.update_time = datetime.datetime.now()
            task.save()

        job = scheduler.get_job(job_id)
        next_run = job.next_run_time if job else None
        next_run_str = next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else "N/A"

        log_success(f"添加生成任务成功: {job_id}")
        log_info(f"  - 小说名: {novel_name}")
        log_info(f"  - Cron: {cron}")
        log_info(f"  - 章节数: {chapter_count}")
        log_info(f"  - 下次执行时间: {next_run_str}")
        return True
    except Exception as e:
        log_error(f"添加生成任务失败: {e}")
        return False

def add_multithread_generate_job(job_id: str, cron: str, novel_name: str, chapter_count: int, thread_count: int):
    """添加定时多线程生成音频任务"""
    try:
        second, minute, hour, day, month, day_of_week, year = parse_cron(cron)

        trigger = create_cron_trigger(second, minute, hour, day, month, day_of_week, year)

        scheduler.add_job(
            execute_multithread_generate_task,
            trigger=trigger,
            id=job_id,
            name=f"定时多线程生成任务_{novel_name}",
            args=[job_id, novel_name, chapter_count, thread_count],
            replace_existing=True
        )

        db = get_db()
        task, created = ScheduledTask.get_or_create(
            job_id=job_id,
            defaults={
                'job_type': 'multithread_generate',
                'cron': cron,
                'novel_name': novel_name,
                'chapter_count': chapter_count,
                'thread_count': thread_count,
                'is_active': True,
                'update_time': datetime.datetime.now()
            }
        )

        if not created:
            task.job_type = 'multithread_generate'
            task.cron = cron
            task.novel_name = novel_name
            task.chapter_count = chapter_count
            task.thread_count = thread_count
            task.is_active = True
            task.update_time = datetime.datetime.now()
            task.save()

        job = scheduler.get_job(job_id)
        next_run = job.next_run_time if job else None
        next_run_str = next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else "N/A"

        log_success(f"添加多线程生成任务成功: {job_id}")
        log_info(f"  - 小说名: {novel_name}")
        log_info(f"  - Cron: {cron}")
        log_info(f"  - 章节数: {chapter_count}")
        log_info(f"  - 线程数: {thread_count}")
        log_info(f"  - 下次执行时间: {next_run_str}")
        return True
    except Exception as e:
        log_error(f"添加多线程生成任务失败: {e}")
        return False

def remove_job(job_id: str):
    """删除定时任务"""
    try:
        scheduler.remove_job(job_id)
        log_info(f"从调度器删除任务: {job_id}")

        db = get_db()
        task = ScheduledTask.select().where(ScheduledTask.job_id == job_id).first()
        if task:
            task.is_active = False
            task.save()
            log_info(f"已标记任务为停用: {job_id}")

        log_success(f"删除任务成功: {job_id}")
        return True
    except Exception as e:
        log_error(f"删除任务失败: {e}")
        return False

def get_all_jobs():
    """获取所有定时任务"""
    try:
        jobs = scheduler.get_jobs()
        result = []
        for job in jobs:
            next_run = job.next_run_time
            result.append({
                "id": job.id,
                "name": job.name,
                "next_run_time": next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else None,
                "trigger": str(job.trigger)
            })
        return result
    except Exception as e:
        log_error(f"获取任务列表失败: {e}")
        return []

def load_jobs_from_database():
    """从数据库加载所有任务到调度器"""
    log_info(f"正在从数据库加载定时任务...")
    try:
        db = get_db()
        tasks = ScheduledTask.select().where(ScheduledTask.is_active == True)
        loaded_count = 0

        for task in tasks:
            try:
                second, minute, hour, day, month, day_of_week, year = parse_cron(task.cron)
                trigger = create_cron_trigger(second, minute, hour, day, month, day_of_week, year)

                if task.job_type == 'parse':
                    scheduler.add_job(
                        execute_parse_task,
                        trigger=trigger,
                        id=task.job_id,
                        name=f"定时解析任务_{task.novel_name}",
                        args=[task.job_id, task.novel_name, task.chapter_count, task.thread_count],
                        replace_existing=True
                    )
                    log_info(f"已加载解析任务: {task.job_id}")
                elif task.job_type == 'generate':
                    scheduler.add_job(
                        execute_generate_task,
                        trigger=trigger,
                        id=task.job_id,
                        name=f"定时生成任务_{task.novel_name}",
                        args=[task.job_id, task.novel_name, task.chapter_count],
                        replace_existing=True
                    )
                    log_info(f"已加载生成任务: {task.job_id}")
                elif task.job_type == 'multithread_generate':
                    scheduler.add_job(
                        execute_multithread_generate_task,
                        trigger=trigger,
                        id=task.job_id,
                        name=f"定时多线程生成任务_{task.novel_name}",
                        args=[task.job_id, task.novel_name, task.chapter_count, task.thread_count],
                        replace_existing=True
                    )
                    log_info(f"已加载多线程生成任务: {task.job_id}")
                elif task.job_type == 'watchdog':
                    scheduler.add_job(
                        execute_watchdog_task,
                        trigger=trigger,
                        id=task.job_id,
                        name=f"看门狗任务_{task.novel_name}",
                        args=[task.job_id, task.novel_name, task.chapter_count, task.thread_count],
                        replace_existing=True
                    )
                    log_info(f"已加载看门狗任务: {task.job_id}")

                loaded_count += 1
            except Exception as job_error:
                log_error(f"加载任务 {task.job_id} 时出错: {job_error}")

        log_success(f"从数据库加载了 {loaded_count} 个定时任务")
        return loaded_count
    except Exception as e:
        log_error(f"从数据库加载任务失败: {e}")
        return 0

def get_parse_task_status():
    """获取解析任务状态"""
    return {
        "running": parse_task_running,
        "current_job_id": parse_current_job_id
    }

def get_generate_task_status():
    """获取生成任务状态"""
    return {
        "running": generate_task_running,
        "current_job_id": generate_current_job_id
    }

def get_multithread_generate_task_status():
    """获取多线程生成任务状态"""
    return {
        "running": multithread_generate_task_running,
        "current_job_id": multithread_generate_current_job_id
    }

def get_watchdog_task_status():
    """获取看门狗任务状态"""
    return {
        "running": watchdog_task_running,
        "current_job_id": watchdog_current_job_id
    }

def add_watchdog_job(job_id: str, cron: str, novel_name: str = '', chapter_count: int = 0, thread_count: int = 0):
    """添加看门狗任务"""
    try:
        second, minute, hour, day, month, day_of_week, year = parse_cron(cron)

        trigger = create_cron_trigger(second, minute, hour, day, month, day_of_week, year)

        scheduler.add_job(
            execute_watchdog_task,
            trigger=trigger,
            id=job_id,
            name=f"看门狗任务_{novel_name}",
            # 传递真实参数，以便RTF恢复后cron能执行批量生成
            args=[job_id, novel_name, chapter_count, thread_count],
            replace_existing=True
        )

        # 立即执行一次生成任务（不等待 cron）
        # 注意：强制设置 needs_batch_execute=True，确保新任务会执行一次
        batch_generate_state['needs_batch_execute'] = True
        log_info(f"🐕 立即开始执行批量生成任务...")
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(execute_watchdog_task(
                job_id=job_id,
                novel_name=novel_name,
                chapter_count=chapter_count,
                thread_count=thread_count,
                log_callback=None
            ))
        except Exception as e:
            log_error(f"创建即时任务失败: {e}")

        db = get_db()
        task, created = ScheduledTask.get_or_create(
            job_id=job_id,
            defaults={
                'job_type': 'watchdog',
                'cron': cron,
                'novel_name': novel_name,
                'chapter_count': chapter_count,
                'thread_count': thread_count,
                'is_active': True,
                'update_time': datetime.datetime.now()
            }
        )

        if not created:
            task.job_type = 'watchdog'
            task.cron = cron
            task.novel_name = novel_name
            task.chapter_count = chapter_count
            task.thread_count = thread_count
            task.is_active = True
            task.update_time = datetime.datetime.now()
            task.save()

        job = scheduler.get_job(job_id)
        next_run = job.next_run_time if job else None
        next_run_str = next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else "N/A"

        log_success(f"添加看门狗任务成功: {job_id}")
        log_info(f"  - 小说名: {novel_name}")
        log_info(f"  - Cron: {cron}")
        log_info(f"  - 章节数: {chapter_count}")
        log_info(f"  - 线程数: {thread_count}")
        log_info(f"  - 下次执行时间: {next_run_str}")
        return True
    except Exception as e:
        log_error(f"添加看门狗任务失败: {e}")
        return False

def start_scheduler():
    """启动调度器"""
    if not scheduler.running:
        log_info(f"正在启动定时任务调度器...")
        scheduler.start()
        load_jobs_from_database()
        log_success(f"定时任务调度器已启动")

def stop_scheduler():
    """停止调度器"""
    if scheduler.running:
        log_info(f"正在停止定时任务调度器...")
        scheduler.shutdown()
        log_success(f"定时任务调度器已停止")

def get_task_details(job_id: str):
    """获取任务详细信息，包括最近5次执行时间"""
    try:
        job = scheduler.get_job(job_id)
        if not job:
            return None

        db = get_db()
        db_task = ScheduledTask.select().where(ScheduledTask.job_id == job_id).first()

        next_run_times = []
        if hasattr(job.trigger, 'get_next_run_time'):
            from datetime import timedelta
            base_time = datetime.datetime.now()
            for i in range(5):
                next_time = job.trigger.get_next_run_time(base_time + timedelta(minutes=i))
                if next_time:
                    next_run_times.append(next_time.strftime("%Y-%m-%d %H:%M:%S"))

        return {
            "job_id": job_id,
            "name": job.name,
            "job_type": db_task.job_type if db_task else "unknown",
            "novel_name": db_task.novel_name if db_task else "unknown",
            "chapter_count": db_task.chapter_count if db_task else 0,
            "thread_count": db_task.thread_count if db_task else 0,
            "cron": db_task.cron if db_task else "",
            "is_active": db_task.is_active if db_task else False,
            "next_run_times": next_run_times,
            "trigger": str(job.trigger)
        }
    except Exception as e:
        log_error(f"获取任务详情失败: {e}")
        return None

def get_all_task_details():
    """获取所有任务的详细信息"""
    try:
        jobs = scheduler.get_jobs()
        details = []
        for job in jobs:
            detail = get_task_details(job.id)
            if detail:
                details.append(detail)
        return details
    except Exception as e:
        log_error(f"获取所有任务详情失败: {e}")
        return []
