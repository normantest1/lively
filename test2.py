import asyncio
import json
import os
import time
import traceback
from typing import List, Dict, Optional, Callable
import anthropic
from asyncio import Queue

from anthropic.types import ThinkingConfigDisabledParam

from bean.beans import Novel, NovelName


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
class DynamicConcurrentProcessor:
    """
    使用 Anthropic SDK 的动态并发处理器
    - 始终保持固定数量的并发请求
    - 一个请求完成，立即启动下一个
    - 自动管理任务队列
    """

    def __init__(self, config: Config):
        self.config = config

        # 初始化 Anthropic 客户端
        self.client = anthropic.Anthropic(
            api_key=config.get("api_key"),
            base_url=config.get("base_url", "https://api.anthropic.com")
        )
        print("key："+config.get("api_key"))
        print("url："+config.get("base_url"))
        print("name："+config.get("model_name"))
        # 获取配置参数
        self.model_name = config.get("model_name")
        self.max_concurrent_requests = int(config.get("max_concurrent_requests", 5))
        self.timeout = int(config.get("timeout", 120))

        # 任务队列
        self.task_queue = Queue()  # 待处理的文本
        self.result_queue = Queue()  # 处理结果

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

    async def send_request(self, task_id: int, text: str) -> Dict:
        """
        发送单个请求到 Anthropic API
        使用 client.messages.create() 方法
        """
        try:
            # 使用同步方法，但在线程池中运行以避免阻塞事件循环
            loop = asyncio.get_event_loop()

            # client.messages.create 是同步方法，需要在线程池中执行
            # response = await loop.run_in_executor(
            #     None,
            #     lambda: self.client.messages.create(
            #         model=self.model_name,
            #         messages=[
            #             {
            #                 "role": "user",
            #                 "content": text
            #             }
            #         ],
            #         max_tokens=2048,
            #         system="你是一位小说信息识别请，请解析我发给你的规则和json文本，只需要将json结果返回给我即可，请注意，你只需要发送纯粹的json字符串即可，不需要md格式的，我需要配合程序解析,请不用返回你思考的内容或关闭思考模式，我想提升速度"
            #     )
            # )
            # content =""
            # # 提取响应内容
            # for block in response.content:
            #     if block.type == "text":
            #         content = block.text
            # content = response.content[0].text if response.content else ""
            # print("响应的内容：========================")
            # print(response)
            # content = response.content.type if response.content.type == "text"
            # print("响应内容结束=======================")
            full_response_text = ""

            async with self.client.messages.stream(
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
                async for chunk in stream.text_stream:
                    full_response_text += chunk
                    print(chunk, end="", flush=True)

            content = full_response_text
            return {
                'task_id': task_id,
                'status': 'success',
                'content': content,
                'raw_response': {
                    'id': response.id,
                    'model': response.model,
                    'stop_reason': response.stop_reason,
                    'usage': {
                        'input_tokens': response.usage.input_tokens,
                        'output_tokens': response.usage.output_tokens
                    }
                },
                'timestamp': time.time()
            }

        except Exception as e:
            # e.with_traceback()
            traceback.print_exc()
            return {
                'task_id': task_id,
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

                print(f"[Worker-{worker_id}] 开始处理任务 {task_id} (剩余队列: {self.task_queue.qsize()})")

                # 发送请求
                result = await self.send_request(task_id, text)
                print("请求的处理结果：")
                print(result)
                print("======================================")
                # 更新统计
                if result['status'] == 'success':
                    self.stats['completed'] += 1
                    print(
                        f"[Worker-{worker_id}] ✓ 任务 {task_id} 完成 ({self.stats['completed']}/{self.stats['total']})")
                else:
                    self.stats['failed'] += 1
                    print(
                        f"[Worker-{worker_id}] ✗ 任务 {task_id} 失败: {result.get('error')} ({self.stats['failed']}/{self.stats['total']})")

                # 将结果放入结果队列
                await self.result_queue.put(result)

                # 触发进度回调
                if self.on_progress_callback:
                    processed = self.stats['completed'] + self.stats['failed']
                    await self.on_progress_callback(processed, self.stats['total'])

                # 标记任务完成
                self.task_queue.task_done()

            except Exception as e:
                print(f"[Worker-{worker_id}] 异常: {e}")
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

    async def process(self, texts: List[str], on_progress: Optional[Callable] = None) -> List[Dict]:
        """
        处理文本列表

        Args:
            texts: 待处理的文本列表
            on_progress: 进度回调函数 async def on_progress(processed, total)

        Returns:
            处理结果列表
        """
        # 初始化
        self.stats = {
            'total': len(texts),
            'completed': 0,
            'failed': 0,
            'start_time': time.time(),
            'end_time': None
        }
        self.on_progress_callback = on_progress

        print(f"\n{'=' * 60}")
        print(f"开始处理 {len(texts)} 个文本")
        print(f"并发数: {self.max_concurrent_requests}")
        print(f"模型: {self.model_name}")
        print(f"{'=' * 60}\n")

        start_time = time.time()

        # 1. 将所有任务放入队列
        for i, text in enumerate(texts):
            await self.task_queue.put({
                'id': i,
                'text': text
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
        await self.task_queue.join()  # 等待队列中的所有任务被处理

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

        print(f"\n{'=' * 60}")
        print(f"处理完成！")
        print(f"总任务数: {self.stats['total']}")
        print(f"成功: {self.stats['completed']}")
        print(f"失败: {self.stats['failed']}")
        print(f"总耗时: {elapsed:.2f} 秒")
        # print(f"平均每个任务: {elapsed / self.stats['total']:.2f} 秒")
        # print(f"吞吐量: {self.stats['total'] / elapsed:.2f} 任务/秒")
        print(f"{'=' * 60}\n")

        return results


# ============ 带解析功能的处理器 ============
class DynamicConcurrentProcessorWithParser(DynamicConcurrentProcessor):
    """
    带解析功能的动态并发处理器
    - 保持固定并发请求
    - 支持自定义解析逻辑
    """

    def __init__(self, config: Config, parser_func: Optional[Callable] = None):
        super().__init__(config)
        self.parser_func = parser_func

    async def parse_result(self, result: Dict) -> Dict:
        """解析结果"""
        if result['status'] == 'success' and self.parser_func:
            try:
                # 在线程池中执行解析（避免阻塞事件循环）
                loop = asyncio.get_event_loop()
                parsed = await loop.run_in_executor(None, self.parser_func, result)
                result['parsed'] = parsed
            except Exception as e:
                result['parse_error'] = str(e)
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

    async def process(self, texts: List[str], on_progress: Optional[Callable] = None) -> List[Dict]:
        """重写process方法，使用带解析的结果收集器"""
        # 初始化
        self.stats = {
            'total': len(texts),
            'completed': 0,
            'failed': 0,
            'start_time': time.time(),
            'end_time': None
        }
        self.on_progress_callback = on_progress

        print(f"\n{'=' * 60}")
        print(f"开始处理 {len(texts)} 个文本")
        print(f"并发数: {self.max_concurrent_requests}")
        print(f"模型: {self.model_name}")
        print(f"{'=' * 60}\n")

        start_time = time.time()

        # 1. 将所有任务放入队列
        for i, text in enumerate(texts):
            await self.task_queue.put({
                'id': i,
                'text': text
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

        print(f"\n{'=' * 60}")
        print(f"处理完成！")
        print(f"总任务数: {self.stats['total']}")
        print(f"成功: {self.stats['completed']}")
        print(f"失败: {self.stats['failed']}")
        print(f"总耗时: {elapsed:.2f} 秒")
        # print(f"平均每个任务: {elapsed / self.stats['total']:.2f} 秒")
        print(f"{'=' * 60}\n")

        return results


# ============ 使用示例 ============
async def main():
    # ========== 方式1：使用配置文件 ==========
    # 创建配置文件 config.json
    # {
    #     "api_key": "sk-ant-api03-xxx",
    #     "base_url": "https://api.anthropic.com",
    #     "model_name": "claude-3-5-sonnet-20241022",
    #     "max_concurrent_requests": 5
    # }

    config = Config("config.json")
    config = Config()
    config.config_data = {
        "api_key": "sk-cp-p2d06RXci2EZxJavRFpptAWoCT5y6UJCbNRFnrkLRL0-EdwdwogeH3siLguGSazQU0DGG50rIVW-FgFwYVxPqXU0fAzTZEmYHt4fm3NhdKD_wr3KVn5jejo",
        "base_url": "https://api.minimaxi.com/anthropic",
        "model_name": "MiniMax-M2.7"
    }
    # 或者直接设置
    # config = Config()
    # config.config_data = {
    #     "api_key": "your-api-key",
    #     "base_url": "https://api.anthropic.com",
    #     "model_name": "claude-3-5-sonnet-20241022"
    # }

    # 准备2000个测试文本
    texts = []
    # texts = ["你好","请描述一下自己","现在几点"]

    novel_list = Novel.select().where(
        (Novel.novel_name == "沧元图") &
        (Novel.current_state == 1)
    ).limit(10)
    with open("./asset/prompt.txt", "r", encoding="utf-8") as file:
        prompt_text = file.read()
    for novel in novel_list:
        texts.append(prompt_text + novel.section_data_json)

    # 创建处理器
    processor = DynamicConcurrentProcessor(config)

    # 定义进度回调
    async def on_progress(processed, total):
        percentage = (processed / total) * 100
        print(f"📊 总体进度: {processed}/{total} ({percentage:.1f}%)")

    # 开始处理
    results = await processor.process(texts, on_progress=on_progress)

    # 查看结果示例
    print("\n前3个结果示例:")
    for result in results[:3]:
        if result['status'] == 'success':
            print(f"\n任务 {result['task_id']}:")
            print(f"内容: {result['content'][:200]}...")
            print(f"Token使用: {result['raw_response']['usage']}")
        else:
            print(f"\n任务 {result['task_id']}: 失败 - {result['error']}")

    # ========== 方式2：带自定义解析函数 ==========
    def custom_parser(result):
        """自定义解析函数"""
        content = result.get('content', '')

        # 这里放你的解析逻辑
        parsed = {
            'length': len(content),
            'word_count': len(content.split()),
            'first_200_chars': content[:200],
            # 添加更多解析字段...
        }
        return parsed

    # 创建带解析的处理器
    processor_with_parse = DynamicConcurrentProcessorWithParser(config, parser_func=custom_parser)

    # 处理少量文本测试
    test_texts = texts[:10]
    results_with_parse = await processor_with_parse.process(test_texts)

    # 查看解析结果
    for result in results_with_parse[:3]:
        if result['status'] == 'success':
            print(f"\n任务 {result['task_id']} 解析结果:")
            print(json.dumps(result['parsed'], ensure_ascii=False, indent=2))


# ============ 简化版：单次使用 ============
async def simple_example():
    """简化版使用示例"""
    # 直接传入配置
    config = Config()
    config.config_data = {
        "api_key": "sk-cp-p2d06RXci2EZxJavRFpptAWoCT5y6UJCbNRFnrkLRL0-EdwdwogeH3siLguGSazQU0DGG50rIVW-FgFwYVxPqXU0fAzTZEmYHt4fm3NhdKD_wr3KVn5jejo",
        "base_url": "https://api.minimaxi.com/anthropic",
        "model_name": "MiniMax-M2.7"
    }

    processor = DynamicConcurrentProcessor(config)
    texts = []
    # 处理少量文本
    novel_list = Novel.select().where(
        (Novel.novel_name == "沧元图") &
        (Novel.current_state == 1)
    ).limit(15)
    with open("./asset/prompt.txt","r",encoding="utf-8") as file:
        prompt_text = file.read()
    for novel in novel_list:
        texts.append(prompt_text+novel.section_data_json)
    results = await processor.process(texts)

    for result in results:
        if result['status'] == 'success':
            print(result['content'])


if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())
    # config = Config()
    # config.config_data = {
    #     "api_key": "sk-cp-p2d06RXci2EZxJavRFpptAWoCT5y6UJCbNRFnrkLRL0-EdwdwogeH3siLguGSazQU0DGG50rIVW-FgFwYVxPqXU0fAzTZEmYHt4fm3NhdKD_wr3KVn5jejo",
    #     "base_url": "https://api.minimaxi.com/anthropic",
    #     "model_name": "MiniMax-M2.7"
    # }
    # client = anthropic.Anthropic(
    #     api_key=config.get("api_key"),
    #     base_url=config.get("base_url", "https://api.anthropic.com")
    # )
    # with open("temp6.json","r",encoding="utf-8") as file:
    #     text = file.read()
    # response = client.messages.create(
    #     model=config.get("model_name"),
    #     messages=[
    #         {
    #             "role": "user",
    #             "content": text
    #         }
    #     ],
    #     max_tokens=20480,
    #     system="你是一位小说信息识别请，请解析我发给你的规则和json文本，只需要将json结果返回给我即可，请注意，你只需要发送纯粹的json字符串即可，不需要md格式的，我需要配合程序解析,请不用返回你思考的内容或关闭思考模式，我想提升速度"        # 可以配置
    # )
    # print(response)