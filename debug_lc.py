import sys
print(sys.executable)
try:
    import langchain
    print(f"LangChain version: {langchain.__version__}")
    print(f"LangChain file: {langchain.__file__}")
    import langchain.chains
    print("langchain.chains imported successfully")
except ImportError as e:
    print(f"Error: {e}")
except Exception as e:
    print(f"Other Error: {e}")
