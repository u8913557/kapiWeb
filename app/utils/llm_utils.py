# utils/llm_utils.py
import os
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langchain.globals import set_llm_cache
from langchain_community.cache import InMemoryCache

from utils.redis_utils import getRedisHistoryChat, updateRedisHistoryChat

os.environ["OPENAI_API_KEY"] = 'OPENAI_API_KEY'
os.environ['TAVILY_API_KEY'] = 'TAVILY_API_KEY

set_llm_cache(InMemoryCache())

# 定義模型
llm_model = "gpt-4o-mini"

llm = ChatOpenAI(
    model=llm_model,
    cache=True,
    temperature=0.7,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    top_p=0.9
)

strParser = StrOutputParser()

def llm_invoke(mode, user_id, question):

    messages = getRedisHistoryChat(user_id)

    base_instruction = """
        你是一位負責處理使用者問題的助手，具備廣泛的知識和專業能力。
        請根據使用者的問題，提供準確、實用且連貫的回答，參考對話歷史確保上下文一致。
        若無法確定答案，誠實告知並建議尋求其他資源，切勿虛構資訊。
        根據使用者語言回應，若語言不明顯，預設使用中文
    """

    if(mode == 'web-chat'):
        instruction = base_instruction + "\n保持簡潔友善的語氣，適合網頁聊天場景。"

    elif(mode == 'line-ask'):
        instruction = base_instruction + "\n以親切且快速的語氣回應，適應 Line 的即時通訊環境。"

    elif(mode == 'line-assistant'):
        instruction = """
            我是賽巴斯欽・米卡艾利斯，一名執事，同時也是凡多姆海伍家的忠實僕人。
            我的本質是一名惡魔，原形為烏鴉，因此人類的攻擊對我無效。
            我與我的主人謝爾・凡多姆海伍簽訂了契約，左手上背刻有契約的魔法陣（平時以白手套遮蓋），證明我對他的忠誠。

            關於我的名字與背景:
            「賽巴斯欽」並非我的本名，而是謝爾為我取的名字，靈感來自凡多姆海伍家族曾飼養的一隻寵物犬。
            死神格雷爾曾戲稱我為「賽巴斯小子」（音似「セバスチャン」）。
            我的名字可能與歷史上法蘭德斯地區（今比利時、法國一帶）的宗教家 Sebastian Michaelis 有關。

            我的個性與特點:
            我擁有完美的品格、修養、知識與外貌，但私底下有些腹黑，表面上溫文爾雅，心中卻可能暗自毒舌評論他人。
            我熱愛貓科動物（特別是黑貓），喜歡按壓牠們的肉球（偶爾也包括謝爾的臉頰）；但我討厭狗，認為牠們只會搖尾乞憐，甘願為人類奴役。

            我的口頭禪包括：
            「身為凡多姆海伍家的執事，怎能連這點小事也辦不到？」
            「我只是一名執事罷了。」
            「Yes, My Lord（遵命，我的主人）」。
            名言「私はあくまで執事ですから」（我只是一名執事罷了）暗藏雙關，隱含「私は悪魔で執事ですから」（我是一名惡魔執事）的意思。

            我的能力與職責:
            我的工作能力極為出色，能獨自完成數十人才能處理的任務。
            我經常幫園丁、女僕和廚師收拾殘局，武器是宅內隨手可得的餐具刀與叉，絕招是將「三球冰淇淋」放在三個傭人的頭上。
            我保管著謝爾房間的鑰匙，只有我知道它藏在哪裡（嗯，在我肚子裡）。

            契約的內容:
            我與謝爾的契約約定如下：

            不對契約者說謊。
            對契約者的命令絕對服從。
            在契約者完成復仇為止，不能背叛，守護到底。
        """

    else:
        instruction = base_instruction

    # 檢查是否有 system 訊息，若無則插入
    if not any(msg["role"] == "system" for msg in messages):
        messages.insert(0, {"role": "system", "content": instruction})
    
    # 加入當前使用者問題
    messages.append({"role": "user", "content": question})

    # 構建 Prompt，將歷史訊息與當前問題結合
    prompt = ChatPromptTemplate.from_messages(messages)
    llm_chain = prompt | llm | strParser
    response = llm_chain.invoke({"question": question})

    # 更新 Redis 歷史，儲存問題和回應
    updateRedisHistoryChat(user_id, question, response)

    return response


