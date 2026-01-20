from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
# from langchain.chat_models import ChatOpenAI

def format_docs(docs):
    return "context"

def test_chain():
    try:
        prompt = ChatPromptTemplate.from_template("{context} {input}")
        
        # Test RunnablePassthrough.assign with lambda
        print("Testing assign with lambda...")
        chain = RunnablePassthrough.assign(context=lambda x: format_docs(x.get("context", [])))
        print("Success: RunnablePassthrough.assign created")
        
        print("Testing chain composition...")
        full_chain = chain | prompt | StrOutputParser()
        print("Success: Chain composed")
        
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_chain()
