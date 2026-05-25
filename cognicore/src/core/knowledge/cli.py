#!/usr/bin/env python3
"""
knowledge base管理 CLI
用法:
  python -m src.core.knowledge.cli index
  python -m src.core.knowledge.cli search "关键词"
  python -m src.core.knowledge.cli ask "问题"
  python -m src.core.knowledge.cli stats
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
import argparse
import logging
from src.core.memory.chromadb_memory import ChromaDBMemory
from src.core.knowledge.kb_indexer import KnowledgeBaseIndexer
from src.core.knowledge.rag_engine import RAGEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


def cmd_index(args):
    chroma = ChromaDBMemory(collection_name="knowledge_base")
    indexer = KnowledgeBaseIndexer(
        chroma_memory=chroma,
        vault_path=args.vault or "/media/wl/D盘/Epanwj/obsidian/全能型knowledge base",
    )
    result = indexer.run_full_index()
    total = result.get('chunks_total', 0)
    new_ = result.get('chunks_new', 0)
    removed = result.get('chunks_removed', 0)
    elapsed = result.get('elapsed_seconds', 0)
    print(f"\nIndexing complete: {total}  chunks"
          f" (新增 {new_}, 清理 {removed})"
          f" Time taken {elapsed}s")


def cmd_search(args):
    chroma = ChromaDBMemory(collection_name="knowledge_base")
    rag = RAGEngine(chroma_memory=chroma)
    results = rag.search(args.query, args.k)
    if not results:
        print("No relevant results found.")
        return
    print(f"\nFound {len(results)} relevant results:\n")
    for i, r in enumerate(results, 1):
        print(f"{'='*60}")
        print(f"[{i}] Source: {r['source']}")
        if r.get("section"):
            print(f"    Section: {r['section']}")
        print(f"    Similarity: {r['score']:.4f}")
        print(f"    Preview: {r['content'][:200]}...")
    print(f"\n{'='*60}")


def cmd_ask(args):
    chroma = ChromaDBMemory(collection_name="knowledge_base")
    rag = RAGEngine(chroma_memory=chroma)
    result = rag.ask(args.question, args.k)
    print(f"\nAnswer:\n{result.answer}\n")
    if result.sources:
        print("References:")
        for s in result.sources:
            print(f"  - {s['file']}" + (f" / {s['section']}" if s.get("section") else ""))


def cmd_stats(args):
    chroma = ChromaDBMemory(collection_name="knowledge_base")
    try:
        collection = chroma.client.get_collection("knowledge_base")
        count = collection.count()
        print(f"\nKnowledge base status:")
        print(f"  Collection: {collection.name}")
        print(f"  Chunk count: {count}")
    except Exception as e:
        print(f"Knowledge base not initialized: {e}")
        print("Please run first: python -m src.core.knowledge.cli index")


def main():
    parser = argparse.ArgumentParser(description="knowledge base管理Tool")
    parser.add_argument("--vault", help="Obsidian Knowledge base path (覆盖默认) ")

    sub = parser.add_subparsers(dest="command")

    p_index = sub.add_parser("index", help="全量索引knowledge base")
    p_index.set_defaults(func=cmd_index)

    p_search = sub.add_parser("search", help="Searchknowledge base")
    p_search.add_argument("query", help="Search关键词")
    p_search.add_argument("-k", type=int, default=5, help="返回数")
    p_search.set_defaults(func=cmd_search)

    p_ask = sub.add_parser("ask", help="基于knowledge base提问")
    p_ask.add_argument("question", help="问题")
    p_ask.add_argument("-k", type=int, default=5, help="检索的片段数")
    p_ask.set_defaults(func=cmd_ask)

    p_stats = sub.add_parser("stats", help="查看Knowledge base status")
    p_stats.set_defaults(func=cmd_stats)

    args = parser.parse_args()
    if args.command:
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
