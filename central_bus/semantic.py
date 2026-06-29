import json
import math
import re
from pathlib import Path
from collections import Counter
from typing import Optional

import numpy as np

PROFILES_PATH = Path(__file__).parent.parent / "bus" / "system" / "semantic_profiles.json"


def _features(text: str) -> list[str]:
    """Extract word tokens + character 3-grams for robust matching across Thai/English."""
    flat = text.lower()
    flat = re.sub(r"[^a-zก-๙0-9\s]", " ", flat)
    words = [t for t in flat.split() if len(t) > 1]
    clean = re.sub(r"\s", "", flat)
    ngrams = [clean[i:i+3] for i in range(len(clean) - 2) if len(clean[i:i+3]) == 3]
    return words + ngrams


class TfidfRouter:
    def __init__(self, profiles_path: Path = PROFILES_PATH):
        raw = json.loads(profiles_path.read_text())
        self.threshold = raw["threshold"]
        self.profiles: dict[str, list[str]] = raw["profiles"]
        self.dept_names: list[str] = list(self.profiles.keys())
        self._build_index()

    def _build_index(self):
        all_sentences = []
        sentence_to_dept = {}
        for dept, sentences in self.profiles.items():
            for s in sentences:
                all_sentences.append(s)
                sentence_to_dept[s] = dept

        featurized = [_features(s) for s in all_sentences]
        self.vocab: dict[str, int] = {}
        for feats in featurized:
            for t in feats:
                if t not in self.vocab:
                    self.vocab[t] = len(self.vocab)

        V = len(self.vocab)
        N = len(all_sentences)
        tfidf_vectors = np.zeros((N, V), dtype=np.float32)

        df = Counter()
        for feats in featurized:
            for t in set(feats):
                if t in self.vocab:
                    df[t] += 1

        idf = np.zeros(V, dtype=np.float32)
        for word, idx in self.vocab.items():
            idf[idx] = math.log((N + 1) / (df[word] + 1)) + 1

        for i, feats in enumerate(featurized):
            tf = Counter(feats)
            for word, count in tf.items():
                if word in self.vocab:
                    idx = self.vocab[word]
                    tfidf_vectors[i, idx] = (1 + math.log(count)) * idf[idx]

        norms = np.linalg.norm(tfidf_vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1
        self.sentence_vectors = tfidf_vectors / norms

        self.sentence_to_dept = sentence_to_dept
        self.sentence_indices: list[str] = all_sentences

    def _vectorize(self, text: str) -> np.ndarray:
        feats = _features(text)
        V = len(self.vocab)
        vec = np.zeros(V, dtype=np.float32)
        tf = Counter(feats)
        N = len(self.sentence_indices)

        for word, count in tf.items():
            if word in self.vocab:
                idx = self.vocab[word]
                df_word = sum(1 for s in self.sentence_indices if word in _features(s))
                idf = math.log((N + 1) / (df_word + 1)) + 1
                vec[idx] = (1 + math.log(count)) * idf

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def match(self, text: str) -> Optional[str]:
        vec = self._vectorize(text)
        scores = self.sentence_vectors @ vec
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])

        if best_score < self.threshold:
            return None

        best_sentence = self.sentence_indices[best_idx]
        return self.sentence_to_dept[best_sentence]

    def match_with_scores(self, text: str) -> dict[str, float]:
        vec = self._vectorize(text)
        dept_scores: dict[str, float] = {}
        for dept in self.dept_names:
            dept_vecs = []
            for i, s in enumerate(self.sentence_indices):
                if self.sentence_to_dept[s] == dept:
                    dept_vecs.append(self.sentence_vectors[i])
            if dept_vecs:
                dept_scores[dept] = float(np.max(np.array(dept_vecs) @ vec))
        return dept_scores
