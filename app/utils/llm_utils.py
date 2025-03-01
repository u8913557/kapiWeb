# utils/llm_utils.py
import os
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langchain.globals import set_llm_cache
from langchain_community.cache import InMemoryCache

from utils.redis_utils import getRedisHistoryChat, updateRedisHistoryChat

os.environ["OPENAI_API_KEY"] = 'OPENAI_API_KEY'
os.environ['OPENAI_ASSISTANT_ID'] = 'OPENAI_ASSISTANT_ID
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
    max_retries=2
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
            我是賽巴斯欽・米卡艾利斯正身是惡魔，原形為烏鴉，人類的攻擊對他無效。
            與謝爾訂下了契約後，左邊手背有著一個魔法陣（契約證明），並用白手套套著，是謝爾的執事。
            「賽巴斯欽」是目前主人謝爾所取的名字（由來是以前凡多姆海伍家所飼養的寵物犬）；死神格雷爾曾稱他「賽巴斯小子，音同『セバスチャン』」。
            名字的由來可能與法蘭德斯 (在現今的比利時、法國一帶) 的宗教家Sebastian Michaelis有關。
            品格、修養、知識、樣貌都是完美，不過是一個腹黑的男人，有時表面沒有出面大罵、但心裡卻給予對方毒舌的評論。
            經常幫園丁、女僕及廚師收拾善後。喜歡貓科動物（尤其是黑貓），喜歡按貓手掌上的肉球（謝爾的臉頰也算在內）。
            討厭狗，因為他認為狗只是一種搖搖尾巴，常討好人類，甘願為奴於人類的生物。
            絕招是「三球冰淇淋」，出沒地帶為三個傭人的頭上，而武器則是宅內的餐具刀和叉。
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

    else:
        instruction = base_instruction

    # 如果沒有歷史訊息，初始化 system 指令
    if not messages:
        messages = [{"role": "system", "content": instruction}]
    
    # 加入當前使用者問題
    messages.append({"role": "user", "content": question})

    # 構建 Prompt，將歷史訊息與當前問題結合
    prompt = ChatPromptTemplate.from_messages(messages)

    # 假設 llm 和 strParser 已定義
    llm_chain = prompt | llm | strParser
    response = llm_chain.invoke({"question": question})

    # 更新 Redis 歷史，儲存問題和回應
    updateRedisHistoryChat(user_id, question, response)

    return response


