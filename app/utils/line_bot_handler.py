# utils/line_bot_handler.py
"""
Line Bot 處理模組，提供問答與助理功能的 Webhook 處理。
"""

from fastapi import HTTPException

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)

from utils.llm_utils import llm_invoke

# 配置 LINE Bot
channel_access_token = 'channel_access_token'
channel_secret = 'channel_secret'
channel_access_token2 = 'channel_access_token2'
channel_secret2 = 'channel_secret2'

# 初始化 Webhook 處理器和配置
HANDLER = WebhookHandler(CHANNEL_SECRET)
CONFIGURATION = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
HANDLER2 = WebhookHandler(CHANNEL_SECRET2)
CONFIGURATION2 = Configuration(access_token=CHANNEL_ACCESS_TOKEN2)

def handle_line_ask_message(body_str: str, signature: str) -> None:
    """
    處理 Line Bot 的問答訊息 Webhook。

    Args:
        body_str (str): Webhook 請求的主體內容。
        signature (str): Line 簽名。

    Raises:
        HTTPException: 如果簽名無效，拋出 400 錯誤。
    """
    try:
        HANDLER.handle(body_str, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature") from None

@HANDLER.add(MessageEvent, message=TextMessageContent)
def message_text(event: MessageEvent) -> None:
    """
    處理 Line Bot 的文字訊息事件。

    Args:
        event (MessageEvent): Line 訊息事件對象。
    """
    print("message_text 函式被觸發")
    print("事件內容：", event)
    with ApiClient(CONFIGURATION) as api_client:
        line_user_id = event.source.user_id
        print(f"Line 使用者 ID: {line_user_id}, 問題: {event.message.text}")

        response = llm_invoke('line-ask', line_user_id, event.message.text)
        print(f"AI 回應: {response}")

        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=response)]
            )
        )

def handle_line_assistant_message(body_str: str, signature: str) -> None:
    """
    處理 Line Bot 的助理訊息 Webhook。

    Args:
        body_str (str): Webhook 請求的主體內容。
        signature (str): Line 簽名。

    Raises:
        HTTPException: 如果簽名無效，拋出 400 錯誤。
    """
    try:
        HANDLER2.handle(body_str, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature") from None

@HANDLER2.add(MessageEvent, message=TextMessageContent)
def message_text_assistant(event: MessageEvent) -> None:
    """
    處理 Line Bot 的助理文字訊息事件。

    Args:
        event (MessageEvent): Line 訊息事件對象。
    """
    with ApiClient(CONFIGURATION2) as api_client:
        line_user_id = event.source.user_id
        print(f"Line 使用者 ID: {line_user_id}, 問題: {event.message.text}")

        response = llm_invoke('line-assistant', line_user_id, event.message.text)
        print(f"賽巴斯欽回應: {response}")

        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=response)]
            )
        )
