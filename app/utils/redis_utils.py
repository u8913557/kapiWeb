# utils/redis_utils.py
"""
Redis 工具模組，用於管理使用者對話歷史。
"""

import os
import json
import redis
from redis.exceptions import ConnectionError


# 初始化 Redis 連線
REDIS_URL = os.environ.get("REDIS_URL", "redis://192.168.11.3:6379")  # 預設為本機 Redis
REDIS_CLIENT = redis.from_url(REDIS_URL)

# 定義過期時間（單位：秒，例如 24 小時）
HISTORY_TTL = 604800  # 24 小時，您可以根據需求調整，例如 3600（1小時）或 604800（7天）

def get_redis_history_chat(user_id: str) -> list:
    """
    從 Redis 獲取指定使用者的對話歷史。

    Args:
        user_id (str): 使用者 ID。

    Returns:
        list: 對話歷史訊息列表，若無則返回空列表。
    """
    messages_key = f"conversation:{user_id}"
    messages = REDIS_CLIENT.get(messages_key)
    if messages:
        return json.loads(messages)
    return []

def update_redis_history_chat(user_id: str, question: str, response: str) -> None:
    """
    更新 Redis 中指定使用者的對話歷史，並設置過期時間。

    Args:
        user_id (str): 使用者 ID。
        question (str): 使用者問題。
        response (str): AI 回應。
    """
    messages_key = f"conversation:{user_id}"
    messages = get_redis_history_chat(user_id)
    messages.append({"role": "user", "content": question})
    messages.append({"role": "assistant", "content": response})
    REDIS_CLIENT.set(messages_key, json.dumps(messages))
    REDIS_CLIENT.expire(messages_key, HISTORY_TTL)

# 測試 Redis 連線（可選）
try:
    REDIS_CLIENT.ping()
    print("成功連線到 Redis 伺服器")
except ConnectionError as e:
    print(f"無法連線到 Redis 伺服器: {e}")
    
