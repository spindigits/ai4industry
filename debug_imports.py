import importlib.util
import sys

def find_module(name):
    spec = importlib.util.find_spec(name)
    if spec:
        print(f"Found {name} at {spec.origin}")
        return True
    else:
        print(f"Could not find {name}")
        return False

print("Executable:", sys.executable)
find_module("langchain")
find_module("langchain.chains")
find_module("langchain.chains.retrieval")
find_module("langchain_core")
find_module("langchain_community")

try:
    from langchain.chains import create_retrieval_chain
    print("SUCCESS: Imported create_retrieval_chain from langchain.chains")
except ImportError:
    print("FAILED: Could not import create_retrieval_chain from langchain.chains")
    # Try finding it elsewhere
    try:
        from langchain.chains.retrieval import create_retrieval_chain
        print("SUCCESS: Imported create_retrieval_chain from langchain.chains.retrieval")
    except ImportError:
        pass
