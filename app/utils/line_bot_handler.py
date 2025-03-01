# utils/line_bot_handler.py
from fastapi import HTTPException

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from langchain.schema import HumanMessage, SystemMessage

from utils.llm_utils import llm_invoke
from utils.redis_utils import getRedisHistoryChat


# 配置 LINE Bot
channel_access_token = 'channel_access_token'
channel_secret = 'channel_secret'

channel_access_token2 = 'channel_access_token2'
channel_secret2 = 'channel_secret2'

handler = WebhookHandler(channel_secret)
configuration = Configuration(access_token=channel_access_token)

handler2 = WebhookHandler(channel_secret2)
configuration2 = Configuration(access_token=channel_access_token2)


def handle_line_ask_message(body_str, signature):

    try:
        handler.handle(body_str, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")


@handler.add(MessageEvent, message=TextMessageContent)
def message_text(event):
    print("message_text 函式被觸發")
    print("事件內容：", event)
    with ApiClient(configuration) as api_client:
        line_user_id = event.source.user_id
        print(f"Line 使用者 ID: {line_user_id}, 問題: {event.message.text}")

        response = llm_invoke('line-ask', line_user_id, event.message.text)
        print(f"AI 回應: {response}")

        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=response)],
            )
        )


def handle_line_assistant_message(body_str, signature):
    try:
        handler2.handle(body_str, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    
@handler2.add(MessageEvent, message=TextMessageContent)
def message_text(event):
    with ApiClient(configuration2) as api_client:
        line_user_id = event.source.user_id
        print(f"Line 使用者 ID: {line_user_id}, 問題: {event.message.text}")

        # 使用 llm_invoke 處理對話
        response = llm_invoke('line-assistant', line_user_id, event.message.text)
        print(f"賽巴斯欽回應: {response}")

        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=response)],
            )
        )
