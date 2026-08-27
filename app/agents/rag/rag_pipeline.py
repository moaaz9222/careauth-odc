import re
import os
import glob
import numpy as np
import tiktoken
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from rank_bm25 import BM25Okapi

EMBEDDING_MODEL = "text-embedding-3-small"

def chunk_policy_text(text: str, document_id: str, document_title: str = "") -> List[Dict[str, Any]]:
    """
    Split markdown policy text by '## §N.N Title' headings.
    Max 500 tokens, 50 token overlap.
    """
    encoding = tiktoken.get_encoding("cl100k_base")
    
    # If no title passed, try to extract from `# Title`
    if not document_title:
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if title_match:
            document_title = title_match.group(1).strip()
        else:
            document_title = document_id.replace("_", " ").title()

    # Regex to match '## §N.N Title'
    pattern = re.compile(r"^(## §\d+\.\d+.*?)(?=\n## §|\Z)", re.MULTILINE | re.DOTALL)
    
    chunks = []
    chunk_index = 0
    matches = list(pattern.finditer(text))
    
    # If no heading matches found, chunk the whole document
    if not matches:
        tokens = encoding.encode(text)
        start = 0
        while start < len(tokens):
            end = min(start + 500, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_str = encoding.decode(chunk_tokens)
            chunks.append({
                "id": f"chunk_{document_id}_{chunk_index:03d}",
                "policy_document_id": document_id,
                "policy_document_title": document_title,
                "chunk_index": chunk_index,
                "section_ref": "§1.0",
                "text": chunk_str,
                "token_count": len(chunk_tokens)
            })
            chunk_index += 1
            if end == len(tokens):
                break
            start += (500 - 50)
        return chunks

    for match in matches:
        section_text = match.group(1).strip()
        
        # Extract section_ref
        header_line = section_text.split('\n')[0]
        ref_match = re.search(r"(§\d+\.\d+)", header_line)
        section_ref = ref_match.group(1) if ref_match else "§1.0"
        
        tokens = encoding.encode(section_text)
        max_tokens = 500
        overlap = 50
        
        start = 0
        while start < len(tokens):
            end = min(start + max_tokens, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_str = encoding.decode(chunk_tokens)
            
            chunks.append({
                "id": f"chunk_{document_id}_{chunk_index:03d}",
                "policy_document_id": document_id,
                "policy_document_title": document_title,
                "chunk_index": chunk_index,
                "section_ref": section_ref,
                "text": chunk_str,
                "token_count": len(chunk_tokens)
            })
            chunk_index += 1
            if end == len(tokens):
                break
            start += (max_tokens - overlap)
            
    return chunks

class RAGPipeline:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL")
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url) if self.api_key else None
        self.embeddings = None
        self.chunks = []
        self.bm25 = None
        self._ensure_policies_loaded()

    def _ensure_policies_loaded(self):
        """Auto-load policy documents from seed directory if not already loaded"""
        if self.chunks:
            return
        
        policy_dir = os.path.join(os.path.dirname(__file__), "..", "..", "seed", "policies")
        if not os.path.exists(policy_dir):
            policy_dir = "app/seed/policies"
            
        all_chunks = []
        if os.path.exists(policy_dir):
            for path in glob.glob(os.path.join(policy_dir, "*.md")):
                filename = os.path.basename(path)
                if filename.lower() == "readme.md":
                    continue
                doc_id = os.path.splitext(filename)[0]
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    file_chunks = chunk_policy_text(content, doc_id)
                    all_chunks.extend(file_chunks)
                except Exception as e:
                    print(f"Warning: Failed to load policy file {path}: {e}")
        
        if all_chunks:
            self.load_chunks(all_chunks)

    async def get_embedding(self, text: str) -> List[float]:
        if not self.client:
            return []
        try:
            response = await self.client.embeddings.create(
                input=[text],
                model=self.embedding_model
            )
            return response.data[0].embedding
        except Exception:
            return []

    def load_chunks(self, chunks: List[Dict[str, Any]]):
        """
        Load chunks and their embeddings/BM25 into memory.
        """
        self.chunks = chunks
        
        valid_embeddings = []
        tokenized_corpus = []
        for c in chunks:
            if c.get("embedding"):
                valid_embeddings.append(c["embedding"])
            tokenized_corpus.append(c["text"].lower().split())
            
        if valid_embeddings and len(valid_embeddings) == len(chunks):
            self.embeddings = np.array(valid_embeddings)
        else:
            self.embeddings = None
            
        if tokenized_corpus:
            self.bm25 = BM25Okapi(tokenized_corpus)

    async def retrieve(self, query: str, top_k: int = 4, floor: float = 0.25) -> List[Dict[str, Any]]:
        self._ensure_policies_loaded()
        if not self.chunks:
            return []
            
        query_embedding = await self.get_embedding(query)
        
        if query_embedding and self.embeddings is not None:
            query_vec = np.array(query_embedding)
            norms = np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_vec)
            norms[norms == 0] = 1e-10
            similarities = np.dot(self.embeddings, query_vec) / norms
            
            top_indices = np.argsort(similarities)[::-1]
            results = []
            for idx in top_indices:
                if len(results) >= top_k:
                    break
                sim = float(similarities[idx])
                if sim >= floor:
                    res = dict(self.chunks[idx])
                    res["similarity"] = round(sim, 3)
                    results.append(res)
            return results
        else:
            # BM25 fallback
            if not self.bm25:
                return []
            tokenized_query = query.lower().split()
            scores = self.bm25.get_scores(tokenized_query)
            top_indices = np.argsort(scores)[::-1]
            
            results = []
            max_score = max(scores) if len(scores) > 0 and max(scores) > 0 else 1.0
            for idx in top_indices[:top_k]:
                # Normalized similarity between 0.30 and 0.85
                raw_score = scores[idx]
                if raw_score <= 0:
                    continue
                normalized_sim = round(min(0.85, max(0.30, 0.30 + (raw_score / max_score) * 0.40)), 2)
                if normalized_sim >= floor:
                    res = dict(self.chunks[idx])
                    res["similarity"] = normalized_sim
                    results.append(res)
            return results
