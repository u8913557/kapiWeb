# utils/redis_utils.py
import os
import redis
import json


# 初始化 Redis 連線
REDIS_URL = os.environ.get("REDIS_URL", "redis://192.168.11.3:6379")  # 預設為本機 Redis
redis_client = redis.from_url(REDIS_URL)

# 定義過期時間（單位：秒，例如 24 小時）
HISTORY_TTL = 604800  # 24 小時，您可以根據需求調整，例如 3600（1小時）或 604800（7天）

def getRedisHistoryChat(user_id):
    # 使用 user_id 作為對話的唯一標識
    messages_key = f"conversation:{user_id}"
    messages = redis_client.get(messages_key)
    if messages:
        return json.loads(messages)
    return []
        

def updateRedisHistoryChat(user_id, question, response):
    messages_key = f"conversation:{user_id}"
    # 從 Redis 讀取當前歷史
    messages = getRedisHistoryChat(user_id)

    # 添加使用者問題和 AI 回應
    messages.append({"role": "user", "content": question})
    messages.append({"role": "assistant", "content": response})

    # 儲存並設置過期時間
    redis_client.set(messages_key, json.dumps(messages))
    redis_client.expire(messages_key, HISTORY_TTL)  # 設置 TTL


# 測試 Redis 連線 (可選)
try:
    redis_client.ping()
    print("成功連線到 Redis 伺服器")
except redis.exceptions.ConnectionError as e:
    print(f"無法連線到 Redis 伺服器: {e}")
