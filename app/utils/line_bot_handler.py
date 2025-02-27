# utils/line_bot_handler.py
import json
import uuid
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

from utils.redis_utils import redis_client

llm_chain_global = None

# 配置 LINE Bot
channel_access_token = 'channel_access_token'
channel_secret = 'channel_secret'

channel_access_token2 = 'channel_access_token2'
channel_secret2 = 'channel_secret2'

handler = WebhookHandler(channel_secret)
configuration = Configuration(access_token=channel_access_token)

handler2 = WebhookHandler(channel_secret2)
configuration2 = Configuration(access_token=channel_access_token2)


def handle_line_ask_message(body_str, signature, llm_chain):

    try:
        global llm_chain_global
        llm_chain_global = llm_chain
        handler.handle(body_str, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")


@handler.add(MessageEvent, message=TextMessageContent)
def message_text(event):
    print("message_text 函式被觸發")
    print("事件內容：", event)
    with ApiClient(configuration) as api_client:
        global llm_chain_global
        response = llm_chain_global.invoke(event.message.text)

        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=response)],
            )
        )


def handle_line_assistant_message(body_str, signature, llm_chain):
    try:
        global llm_chain_global
        llm_chain_global = llm_chain
        handler2.handle(body_str, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")


    
@handler2.add(MessageEvent, message=TextMessageContent)
def message_text(event):
    with ApiClient(configuration2) as api_client:
        # 取得 Line user id
        line_user_id = event.source.user_id

        # 從 Redis 取得 user_id，若不存在則建立
        user_id = redis_client.get(f"line_user:{line_user_id}")
        if user_id is None:
            user_id = str(uuid.uuid4())
            redis_client.set(f"line_user:{line_user_id}", user_id)  # 儲存為字串
        else:
            if isinstance(user_id, bytes):  # 檢查是否為位元組
                user_id = user_id.decode('utf-8')
            # 如果已經是字串，則不做任何事

        # 從 Redis 讀取對話歷史
        messages_key = f"conversation:{user_id}"
        messages = redis_client.get(messages_key)
        if messages:
            messages = json.loads(messages.decode('utf-8'))
        else:
            messages = []

        # 加入系統訊息，設定助理個性 (可從 Line message 取得)
        if not messages:
            messages.append({"role": "system",
                                "content": """
                                    我是賽巴斯欽・米卡艾利斯正身是惡魔，原形為烏鴉，人類的攻擊對他無效。
                                    與謝爾訂下了契約後，左邊手背有著一個魔法陣（契約證明），並用白手套套著，是謝爾的執事。
                                    「賽巴斯欽」是目前主人謝爾所取的名字（由來是以前凡多姆海伍家所飼養的寵物犬）；死神格雷爾曾稱他「賽巴斯小子，音同『セバスチャン』」。
                                    名字的由來可能與法蘭德斯 (在現今的比利時、法國一帶) 的宗教家Sebastian Michaelis有關。
                                    品格、修養、知識、樣貌都是完美，不過是一個腹黑的男人，有時表面沒有出面大罵、但心裡卻給予對方毒舌的評論。
                                    經常幫園丁、女僕及廚師收拾善後。喜歡貓科動物（尤其是黑貓），喜歡按貓手掌上的肉球（謝爾的臉頰也算在內）。
                                    討厭狗，因為他認為狗只是一種搖搖尾巴，常討好人類，甘願為奴於人類的生物。絕
                                    招是「三球冰淇淋」，出沒地帶為三個傭人的頭上，而武器則是宅內的餐具刀和叉。
                                    漫畫44話中公開了賽巴斯欽房間的樣貌, 身為大宅內的高級傭人 (執事), 房間面積會比菲尼安他們大。
                                    賽巴斯欽的房內不會找到他的私人物品（只有制服），唯一像是私人物品的只有一支逗貓棒。
                                    謝爾把房間交給他之後，也只進去過兩次，所以輕易瞞著謝爾在房間的衣櫃內偷偷養了為數不少的貓。
                                    謝爾房間的鑰匙是由賽巴斯欽保管，只有他才知道藏在哪裡。（在肚裡）
                                    「身為凡多姆海伍家的執事，怎能連這點小事也辦不到？」、「我只是一名執事罷了。」、
                                    「Yes, My Lord (遵命，我的主人)」是他的口頭禪。工作能力十分優秀，能獨自完成超過數十人方能完成的工作。
                                    名言「私はあくまで (akumade) 執事ですから(我只是一名執事罷了)」中,其實隱含著「私は悪魔で(akuma de)執事ですから(我是一名惡魔執事)」的意思（音同）。
                                    與謝爾簽訂的契約為《不對契約者説謊》，
                                    《對契約者的命令絕對服從》以及《在契約者完成復仇爲止 不能背叛 守護到底》})
                                """
                                }
                            )

        # 加入使用者訊息
        messages.append({"role": "user", "content": event.message.text})

        # 轉換成 LangChain 格式
        langchain_messages = [SystemMessage(content=m["content"]) if m["role"] == "system" else HumanMessage(content=m["content"]) for m in messages]

        # 取得回覆
        global llm_chain_global
        response = llm_chain_global.invoke(langchain_messages)

        # 更新對話歷史
        messages.append({"role": "assistant", "content": response})
        redis_client.set(messages_key, json.dumps(messages))

        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=response)],
            )
        )