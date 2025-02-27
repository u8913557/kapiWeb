# utils/redis_utils.py
import os
import redis

# 初始化 Redis 連線
REDIS_URL = os.environ.get("REDIS_URL", "redis://192.168.11.3:6379")  # 預設為本機 Redis
redis_client = redis.from_url(REDIS_URL)

# 測試 Redis 連線 (可選)
try:
    redis_client.ping()
    print("成功連線到 Redis 伺服器")
except redis.exceptions.ConnectionError as e:
    print(f"無法連線到 Redis 伺服器: {e}")