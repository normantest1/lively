import traceback
import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from bean.beans import Novel, ScheduledTask, get_db
from parse_text import async_parse_text, parse_novel_data_bind_role_audio
from generate_audio import load_role_audio, generate_chapter_audio
import asyncio

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
parse_current_job_id = None
generate_current_job_id = None
parse_cancel_event = None
generate_cancel_event = None
server_instance = None
task_logs = {}
task_history = {}

def set_server_instance(server):
    """设置全局server实例"""
    global server_instance
    server_instance = server
    log_info(f"定时任务服务已绑定server实例")

def log_info(message: str):
    """统一的信息日志"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [INFO] {message}"
    print(log_line)
    _add_to_logs(log_line)

def log_error(message: str):
    """统一的错误日志"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [ERROR] {message}"
    print(log_line)
    _add_to_logs(log_line)

def log_success(message: str):
    """统一的成功日志"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [SUCCESS] {message}"
    print(log_line)
    _add_to_logs(log_line)

def log_warning(message: str):
    """统一的警告日志"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [WARNING] {message}"
    print(log_line)
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
        day = parse_cron_field(parts[3])
        month = parse_cron_field(parts[4])
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
    """执行批量解析任务"""
    global parse_task_running, parse_current_job_id, parse_cancel_event
    
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
    
    if parse_task_running:
        log_warning(f"发现正在执行的解析任务: {parse_current_job_id}，新任务 {job_id} 将替代旧任务")
        if log_callback:
            await log_callback(f"[警告] 发现正在执行的解析任务: {parse_current_job_id}，新任务将替代旧任务\n")
        
        if parse_cancel_event:
            parse_cancel_event.set()
            log_info(f"已发送取消信号到任务: {parse_current_job_id}")
            if log_callback:
                await log_callback(f"[警告] 已发送取消信号到任务: {parse_current_job_id}\n")
        
        await asyncio.sleep(0.5)
    
    parse_task_running = True
    parse_current_job_id = job_id
    parse_cancel_event = asyncio.Event()
    current_cancel_event = parse_cancel_event
    
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
        novels_to_parse = Novel.select().where(
            Novel.novel_name == novel_name, 
            Novel.current_state == 1
        ).limit(chapter_count)
        
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
        traceback.print_exc()
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
    """执行批量生成音频任务"""
    global generate_task_running, generate_current_job_id, generate_cancel_event, server_instance
    
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
    
    if generate_task_running:
        log_warning(f"发现正在执行的生成任务: {generate_current_job_id}，新任务 {job_id} 将替代旧任务")
        if log_callback:
            await log_callback(f"[警告] 发现正在执行的生成任务: {generate_current_job_id}，新任务将替代旧任务\n")
        
        if generate_cancel_event:
            generate_cancel_event.set()
            log_info(f"已发送取消信号到任务: {generate_current_job_id}")
            if log_callback:
                await log_callback(f"[警告] 已发送取消信号到任务: {generate_current_job_id}\n")
        
        await asyncio.sleep(0.5)
    
    generate_task_running = True
    generate_current_job_id = job_id
    generate_cancel_event = asyncio.Event()
    current_cancel_event = generate_cancel_event
    
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
        traceback.print_exc()
        if log_callback:
            await log_callback(f"[定时任务] 批量生成任务执行失败: {e}\n")
        return False
    finally:
        if generate_current_job_id == job_id:
            generate_task_running = False
            generate_current_job_id = None
            generate_cancel_event = None
        log_info(f"生成任务执行器退出，任务ID: {job_id}")

def add_parse_job(job_id: str, cron: str, novel_name: str, chapter_count: int, thread_count: int):
    """添加定时解析任务"""
    try:
        second, minute, hour, day, month, day_of_week, year = parse_cron(cron)
        
        trigger = create_cron_trigger(second, minute, hour, day, month, day_of_week, year)
        
        scheduler.add_job(
            execute_parse_task,
            trigger=trigger,
            id=job_id,
            name=f"定时解析任务_{novel_name}",
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
        traceback.print_exc()
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
        traceback.print_exc()
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
                
                loaded_count += 1
            except Exception as job_error:
                log_error(f"加载任务 {task.job_id} 时出错: {job_error}")
        
        log_success(f"从数据库加载了 {loaded_count} 个定时任务")
        return loaded_count
    except Exception as e:
        log_error(f"从数据库加载任务失败: {e}")
        traceback.print_exc()
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
