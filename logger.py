"""
日志模块 - 用于将print语句输出同时保存到日志文件
"""
import os
import datetime
import sys
import traceback

_log_file = None
_log_file_path = None

def init_logger():
    """初始化日志系统，创建以启动时间命名的日志文件"""
    global _log_file, _log_file_path

    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)

    now = datetime.datetime.now()
    filename = f"{now.year}年{now.month}月{now.day}日{now.hour}时{now.minute}分{now.second}秒服务器启动日志.log"
    _log_file_path = os.path.join(logs_dir, filename)

    _log_file = open(_log_file_path, 'w', encoding='utf-8')
    _log_file.write(f"=== 服务器启动于 {now.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    _log_file.flush()

    return _log_file_path

def log(message):
    """将消息写入日志文件"""
    global _log_file
    if _log_file:
        _log_file.write(message + '\n')
        _log_file.flush()

def log_error(message: str = None):
    """记录完整的错误信息，包括堆栈跟踪"""
    global _log_file
    if _log_file:
        if message:
            _log_file.write(f"\n{'='*80}\n")
            _log_file.write(f"错误信息: {message}\n")
            _log_file.write(f"{'='*80}\n")
        # 写入完整的堆栈跟踪
        exc_type, exc_value, exc_traceback = sys.exc_info()
        if exc_type is not None:
            _log_file.write("完整错误堆栈:\n")
            traceback.print_exc(file=_log_file)
            _log_file.write('\n')
        _log_file.flush()

def close_logger():
    """关闭日志文件"""
    global _log_file
    if _log_file:
        _log_file.write(f"=== 服务器关闭于 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
        _log_file.close()
        _log_file = None

def get_log_file_path():
    """获取当前日志文件路径"""
    return _log_file_path
