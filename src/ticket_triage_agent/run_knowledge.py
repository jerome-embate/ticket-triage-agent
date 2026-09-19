from ticket_triage_agent.knowledge_base import KnowledgeBase
from ticket_triage_agent.seed_data import kb_articles

def main() -> None:
    kb = KnowledgeBase()
    kb.add_article(kb_articles)

    results = kb.search("Why am I getting rate limited?", top_k=2)
    for chunk, score in results:
        print(f"Score: {score:.4f}, Chunk: {chunk}")


if __name__ == "__main__":
    main()