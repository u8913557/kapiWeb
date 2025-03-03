# utils/redis_utils.py
"""
Redis 工具模組，用於管理使用者對話歷史（使用 redis-py 異步版本，全局連接池）。
"""

import os
import json
from redis.asyncio import Redis
from redis.exceptions import ConnectionError


# Redis 連線配置
REDIS_URL = os.environ.get("REDIS_URL", "redis://192.168.11.3:6379")  # 預設為指定 Redis

# 定義過期時間（單位：秒，例如 24 小時）
HISTORY_TTL = 604800  # 24 小時，您可以根據需求調整，例如 3600（1小時）或 604800（7天）

# 全局 Redis 連接池
redis_pool = None

async def init_redis_pool():
    """初始化全局 Redis 連接池"""
    global redis_pool
    if redis_pool is None:
        redis_pool = await Redis.from_url(
            REDIS_URL,
            decode_responses=True,  # 自動解碼為字符串
            max_connections=10      # 設置最大連接數，可根據需求調整
        )
    print("Redis 連接池已初始化")

async def close_redis_pool():
    """關閉全局 Redis 連接池"""
    global redis_pool
    if redis_pool:
        await redis_pool.aclose()
        print("Redis 連接池已關閉")
        redis_pool = None

async def get_redis_history_chat(user_id: str) -> list:
    """
    從 Redis 獲取指定使用者的對話歷史（異步版本，使用全局連接池）。

    Args:
        user_id (str): 使用者 ID。

    Returns:
        list: 對話歷史訊息列表，若無則返回空列表。
    """
    messages_key = f"conversation:{user_id}"
    try:
        if redis_pool is None:
            await init_redis_pool()
        messages = await redis_pool.get(messages_key)
        if messages:
            return json.loads(messages)
        return []
    except Exception as e:
        logging.error(f"無法獲取 Redis 歷史: {e}")
        return []

async def update_redis_history_chat(user_id: str, question: str, response: str) -> None:
    """
    更新 Redis 中指定使用者的對話歷史，並設置過期時間（異步版本，使用全局連接池）。

    Args:
        user_id (str): 使用者 ID。
        question (str): 使用者問題。
        response (str): AI 回應。
    """
    messages_key = f"conversation:{user_id}"
    try:
        messages = await get_redis_history_chat(user_id)
        messages.append({"role": "user", "content": question})
        messages.append({"role": "assistant", "content": response})
        await redis_pool.set(messages_key, json.dumps(messages))
        await redis_pool.expire(messages_key, HISTORY_TTL)
    except Exception as e:
        print(f"無法更新 Redis 歷史: {e}")

# 測試 Redis 連線（異步版本）
async def test_redis_connection():
    try:
        await redis_pool.ping()
        print("成功連線到 Redis 伺服器（異步，全局連接池）")
    except ConnectionError as e:
        print(f"無法連線到 Redis 伺服器: {e}")

if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(init_redis_pool())
    loop.run_until_complete(test_redis_connection())
    loop.run_until_complete(close_redis_pool())
