from app.services.llama_service import LlamaService

# Global variable to store LlamaService instance
llama_service = None

def get_llama_service() -> LlamaService:
    """
    Dependency to get LlamaService instance
    """
    if llama_service is None:
        raise RuntimeError("LlamaService not initialized")
    return llama_service

def set_llama_service(service: LlamaService):
    """
    Set the global LlamaService instance
    """
    global llama_service
    llama_service = service

# TODO setup llama_index and vector_store and documenrts and connect to ollama