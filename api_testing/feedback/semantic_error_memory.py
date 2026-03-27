import faiss
import numpy as np
import json
import os

class SemanticErrorMemory:

    def __init__(self, embedder, dim=768, threshold=0.9, cache_dir="error_memory.json"):

        self.embedder = embedder
        self.threshold = threshold
        self.path = os.path.join(cache_dir, "error_memory.json")
        self.index = faiss.IndexFlatIP(dim)
        self.meta = []

        self._load()

    def _load(self):

        if not os.path.exists(self.path):
            return

        with open(self.path, "r", encoding="utf-8") as f:
            self.meta = json.load(f)

        if len(self.meta) == 0:
            return

        vectors = np.array([m["embedding"] for m in self.meta]).astype("float32")
        faiss.normalize_L2(vectors)

        self.index.add(vectors)

    def save(self):

        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.meta, f, indent=4)

    def search(self, text):

        if len(self.meta) == 0:
            return None

        emb = np.array([self.embedder.embed(text)]).astype("float32")
        faiss.normalize_L2(emb)

        scores, idx = self.index.search(emb, 1)

        score = scores[0][0]
        i = idx[0][0]

        if score >= self.threshold:
            return self.meta[i]["solution"]

        return None

    def add(self, text, solution):
        # tránh duplicate error
        if any(m["text"] == text for m in self.meta):
            return

        emb = np.array([self.embedder.embed(text)]).astype("float32")
        faiss.normalize_L2(emb)

        self.index.add(emb)

        self.meta.append({
            "text": text,
            "embedding": emb[0].tolist(),
            "solution": solution
        })

        self.save()