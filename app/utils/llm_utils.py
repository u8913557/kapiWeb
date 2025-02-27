# utils/llm_utils.py
import os
from langchain_openai.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langchain.globals import set_llm_cache
from langchain_community.cache import InMemoryCache

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

def create_plain_llm():
    # 定義 Plain LLM
    plain_instruction = """
        你是一位負責處理使用者問題的助手，請利用你的知識來回應問題。
        回應問題時請確保答案的準確性，勿虛構答案。
    """

    plain_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", plain_instruction),
            ("human", "問題: {question}"),
        ]
    )

    plain_llm_chain = plain_prompt | llm | strParser

    return plain_llm_chain