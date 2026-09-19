import re
import numpy as np
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

def chunk_text_with_overlap(text: str, chunk_size: int = 3, overlap: int = 1) -> list[str]:
    """
    Splits the input text into chunks of specified size with a specified overlap.
    
    Args:
        text (str): The input text to be chunked.
        chunk_size (int): The maximum size of each chunk.
        overlap (int): The number of overlapping characters between chunks.
        
    Returns:
        list[str]: A list of text chunks.
    """
    # Clean up the text by removing extra whitespace
    text = text.strip().replace("\n", " ")
    sentences = [re.sub(r'\s+', ' ', s).strip() for s in re.split(r'(?<=[.!?])\s+', text)]
    
    chunks = []
    step = chunk_size - overlap
    for i in range(0, len(sentences), step):
        chunk = " ".join(sentences[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    
    return chunks

class KnowledgeBase:
    def __init__(self) -> None:
        self.chunks: list[str] = []
        self.embeddings: np.ndarray | None = None

    def add_article(self, articles: list[str]) -> None:
        """
        Adds a knowledge base article to the knowledge base, splitting it into chunks and generating embeddings.
        
        Args:
            article (str): The knowledge base article to be added.
        """
        all_chunks: list[str] = []
        for article in articles:
            all_chunks.extend(chunk_text_with_overlap(article, chunk_size=2, overlap=1))

        new_embeddings = model.encode(all_chunks)
        self.chunks.extend(all_chunks)
        if self.embeddings is None:
            self.embeddings = new_embeddings
        else:
            self.embeddings = np.vstack((self.embeddings, new_embeddings))

    def search(self, query: str, top_k: int = 3) -> list[tuple[str, float]]:
        """
        Searches the knowledge base for the most relevant chunks based on the query.
        
        Args:
            query (str): The search query.
            top_k (int): The number of top results to return.   

        """
        if self.embeddings is None or len(self.chunks) == 0:
            return []

        query_embedding = model.encode(query)
        similarities = np.dot(self.embeddings, query_embedding) / (
            np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        )
        top_indices = np.argsort(similarities)[::-1][:top_k]
        return [(self.chunks[i], float(similarities[i])) for i in top_indices]