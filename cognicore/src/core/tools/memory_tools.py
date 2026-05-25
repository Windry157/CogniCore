import json
from typing import List, Dict, Any
from src.core.tools.registry import register_tool
# 假设你的 VectorMemory 在 src.core.memory.vector_memory
from src.core.memory.memory_vector import VectorMemory
from src.core.memory.splitter import TextSplitter

# Initialization单例 (在实际生产中, 这应该由依赖Register入容器管理)
# 确保这里使用的 model_name 与你环境中的可用Model一致
_memory_instance = VectorMemory(model_name="ollama:nomic-embed-text")
_splitter = TextSplitter(chunk_size=500, chunk_overlap=50)

@register_tool(name="save_knowledge")
def save_knowledge(content: str, source: str = "user_interaction") -> str:
    """
    将important infoSave到长期 memories中.
    当你需要记住用户的偏好, 特定的事实, 或者用户明确要求你记住某些Content时使用.
    
    Args:
        content: 需要 memories的具体文本Content.
        source: 信息的Source (默认为 'user_interaction') .
        
    Returns:
        SaveStatus.
    """
    try:
        # 拆分文本
        chunks = _splitter.split_text(content)
        saved_chunks = []
        
        # 逐 SaveChunk
        for i, chunk in enumerate(chunks):
            metadata = {
                "source": source,
                "chunk_id": i,
                "total_chunks": len(chunks),
                "original_length": len(content)
            }
            memory_id = _memory_instance.add_memory(chunk, metadata=metadata)
            saved_chunks.append({
                "id": memory_id,
                "chunk_id": i,
                "length": len(chunk)
            })
        
        return json.dumps({ 
            "status": "success",
            "message": f"saved to memories库, Total {len(saved_chunks)}  chunks",
            "content_preview": content[:50] + "...",
            "chunks": saved_chunks
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)

@register_tool(name="search_knowledge")
def search_knowledge(query: str) -> str:
    """
    From长期 memories中检索相关信息.
    当用户询问过去发生的事情, 或者需要利用之前的上下文来Answer问题时使用.
    
    Args:
        query: Search关键词或自然语言Description.
        
    Returns:
        相关的 memories片段列表和拼接后的上下文.
    """
    try:
        results = _memory_instance.search(query, limit=3, threshold=0.5)
        if not results:
            return json.dumps({"status": "success", "data": [], "context": "", "message": "未Found related memories"}, ensure_ascii=False)
            
        # 精简返回给 LLM 的数据, 节省 Token
        formatted_results = [
            {"content": r["content"], "similarity": round(r["similarity"], 2), "created_at": r["created_at"]}
            for r in results
        ]
        
        # 拼接上下文
        context = "\n".join([r["content"] for r in results])
        
        return json.dumps({"status": "success", "data": formatted_results, "context": context}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)}, ensure_ascii=False)
