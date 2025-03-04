# utils/line_bot_handler.py
"""
Line Bot 處理模組，提供問答與助理功能的 Webhook 處理。
"""

import logging
from linebot.v3 import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import (
    AsyncMessagingApi,
    Configuration,
    ApiClient,
    ReplyMessageRequest,
    TextMessage
)
from fastapi import HTTPException
from utils.llm_utils import llm_invoke

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 配置 LINE Bot
channel_access_token = 'channel_access_token'
channel_secret = 'channel_secret'
channel_access_token2 = 'channel_access_token2'
channel_secret2 = 'channel_secret2'

# 初始化 Webhook 處理器和配置
CONFIGURATION = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
PARSER = WebhookParser(CHANNEL_SECRET)
CONFIGURATION2 = Configuration(access_token=CHANNEL_ACCESS_TOKEN2)
PARSER2 = WebhookParser(CHANNEL_SECRET2)

async def handle_line_ask_message(body_str: str, signature: str) -> None:
    """
    處理 Line Bot 的問答訊息 Webhook。
    """
    try:
        events = PARSER.parse(body_str, signature)
        for event in events:
            if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
                await process_ask_message(event)
    except InvalidSignatureError:
        logger.error("簽名無效")
        raise HTTPException(status_code=400, detail="Invalid signature") from None
    except Exception as e:
        logger.error(f"處理問答訊息時發生錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from None

async def process_ask_message(event: MessageEvent) -> None:
    logger.info("處理問答訊息")
    logger.info(f"事件內容：{event}")

    # 跳過重發事件
    if event.delivery_context.is_redelivery:
        logger.info("此事件為重發事件，跳過處理")
        return

    with ApiClient(CONFIGURATION) as api_client:
        line_user_id = event.source.user_id
        logger.info(f"Line 使用者 ID: {line_user_id}, 問題: {event.message.text}")

        response = await llm_invoke('line-ask', line_user_id, event.message.text)
        logger.info(f"AI 回應: {response}")

        line_bot_api = AsyncMessagingApi(api_client)
        try:
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=response)]
                )
            )
            logger.info("訊息成功回覆")
        except Exception as e:
            logger.error(f"回覆訊息失敗: {str(e)}")
            if "400" in str(e) and "Invalid reply token" in str(e):
                logger.warning("無效的 reply_token，可能是延遲或重發")
                return
            raise

async def handle_line_assistant_message(body_str: str, signature: str) -> None:
    """
    處理 Line Bot 的助理訊息 Webhook。
    """
    try:
        events = PARSER2.parse(body_str, signature)
        for event in events:
            if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
                await process_assistant_message(event)
    except InvalidSignatureError:
        logger.error("簽名無效")
        raise HTTPException(status_code=400, detail="Invalid signature") from None
    except Exception as e:
        logger.error(f"處理助理訊息時發生錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error") from None

async def process_assistant_message(event: MessageEvent) -> None:
    logger.info("處理助理訊息")
    logger.info(f"事件內容：{event}")

    # 跳過重發事件
    if event.delivery_context.is_redelivery:
        logger.info("此事件為重發事件，跳過處理")
        return

    with ApiClient(CONFIGURATION2) as api_client:
        line_user_id = event.source.user_id
        logger.info(f"Line 使用者 ID: {line_user_id}, 問題: {event.message.text}")

        response = await llm_invoke('line-assistant', line_user_id, event.message.text)
        logger.info(f"賽巴斯欽回應: {response}")

        line_bot_api = AsyncMessagingApi(api_client)
        try:
            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=response)]
                )
            )
            logger.info("助理訊息成功回覆")
        except Exception as e:
            logger.error(f"助理回覆訊息失敗: {str(e)}")
            if "400" in str(e) and "Invalid reply token" in str(e):
                logger.warning("無效的 reply_token，可能是延遲或重發")
                return
            raise
