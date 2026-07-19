"""Central Bus v0.6 — Behavior Classifier.

TF-IDF + Logistic Regression classifier for Behavior-Centric Routing.

Architecture
~~~~~~~~~~~~
- **Tier 0**: Behavior Classifier (fast path, <50ms)
- **Classifier**: TF-IDF vectorizer → Multi-class Logistic Regression (pure numpy)
- **Cold start**: Keyword heuristic until trained on enough labeled data
- **Confidence**: Calibrated via softmax probabilities, threshold >=0.9
"""

from __future__ import annotations

import json
import logging
import math
import pickle
import re
from collections import Counter
from pathlib import Path
from typing import Any, Optional

import numpy as np

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Seed Keyword Data
# ---------------------------------------------------------------------------

SEED_KEYWORDS: dict[str, list[str]] = {
    "vision_strategy": ["vision", "strategy", "mission", "direction", "goal", "objective", "strategic", "long-term"],
    "owner_decision": ["final decision", "approve", "escalate", "owner", "authorize", "sign off", "decide"],
    "budget_approval": ["budget", "funding", "allocate", "resource", "approve budget"],
    "cost_analysis": ["cost", "roi", "profit", "revenue", "financial model", "forecast", "expense"],
    "campaign_management": ["campaign", "marketing", "advertising", "promotion", "ad"],
    "brand_strategy": ["brand", "branding", "positioning", "identity"],
    "content_production": ["content", "write", "caption", "copy", "blog", "post", "video", "script", "article"],
    "pipeline_coordination": ["pipeline", "workflow", "orchestrate", "coordinate", "handoff", "cross"],
    "architecture_design": ["architecture", "system design", "schema", "central bus", "adr", "infrastructure"],
    "routing_monitoring": ["routing", "route", "monitor", "health check", "watchdog", "circuit breaker"],
    "feature_definition": ["feature", "prd", "requirement", "user story", "product", "spec", "feature request"],
    "roadmap_planning": ["roadmap", "prioritize", "backlog", "release", "planning", "sprint"],
    "backend_development": ["backend", "api", "database", "server", "microservice", "endpoint"],
    "frontend_development": ["frontend", "ui code", "component", "react", "vue", "html", "css", "tailwind"],
    "bug_fixing": ["bug", "fix", "error", "crash", "defect", "regression", "broken"],
    "visual_design": ["design system", "visual", "style guide", "figma", "component library", "ui design"],
    "ux_research": ["ux", "user research", "usability", "wireframe", "user experience", "research"],
    "qa_testing": ["test", "qa", "quality", "test case", "automation test", "testing"],
    "sales_deal": ["sales", "deal", "proposal", "close", "prospect", "pipeline deal"],
    "customer_support": ["support", "customer", "ticket", "help", "issue", "service"],
    "legal_compliance": ["compliance", "regulatory", "pdpa", "gdpr", "regulation", "compliant"],
    "contract_management": ["contract", "agreement", "nda", "mou", "legal", "document"],
    "smart_contract_defi": ["smart contract", "defi", "solana", "blockchain", "solidity", "anchor", "token", "crypto", "web3"],
    "network_operations": ["network", "cdn", "dns", "vpn", "load balancer", "bandwidth", "infrastructure"],
    "security_incident": ["security", "threat", "vulnerability", "incident", "breach", "attack", "cyber"],
    "behavioral_research": ["psychology", "behavior", "cognitive bias", "user behavior", "bias"],
}

BEHAVIOR_DEPT_MAP: dict[str, str] = {
    "vision_strategy": "ceo",
    "owner_decision": "ceo",
    "budget_approval": "cfo",
    "cost_analysis": "cfo",
    "campaign_management": "cmo",
    "brand_strategy": "cmo",
    "content_production": "content_creator",
    "pipeline_coordination": "orchestrator",
    "architecture_design": "architect",
    "routing_monitoring": "architect",
    "feature_definition": "product",
    "roadmap_planning": "product",
    "backend_development": "engineering",
    "frontend_development": "engineering",
    "bug_fixing": "engineering",
    "visual_design": "design",
    "ux_research": "design",
    "qa_testing": "qa",
    "sales_deal": "sales",
    "customer_support": "support",
    "legal_compliance": "legal",
    "contract_management": "legal",
    "smart_contract_defi": "web3",
    "network_operations": "neteng",
    "security_incident": "cybersec",
    "behavioral_research": "psychology",
}


# ---------------------------------------------------------------------------
# TF-IDF Vectorizer (pure numpy)
# ---------------------------------------------------------------------------


class TfidfVectorizer:
    """TF-IDF vectorizer using word tokens + character 3-grams."""

    def __init__(self, max_features: int = 500) -> None:
        self.max_features = max_features
        self.vocab: dict[str, int] = {}
        self.idf: np.ndarray | None = None
        self._fitted = False

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        flat = text.lower()
        flat = re.sub(r"[^a-z\u0e01-\u0e390-9\s]", " ", flat)
        words = [t for t in flat.split() if len(t) > 1]
        clean = re.sub(r"\s", "", flat)
        ngrams = [clean[i:i+3] for i in range(len(clean) - 2) if len(clean[i:i+3]) == 3]
        return words + ngrams

    def fit(self, texts: list[str]) -> TfidfVectorizer:
        all_feats = [self._tokenize(t) for t in texts]
        N = len(texts)
        vocab_counter: Counter = Counter()
        for feats in all_feats:
            for t in feats:
                vocab_counter[t] += 1
        most_common = vocab_counter.most_common(self.max_features)
        self.vocab = {w: i for i, (w, _) in enumerate(most_common)}
        V = len(self.vocab)
        df = Counter()
        for feats in all_feats:
            for t in set(feats):
                if t in self.vocab:
                    df[t] += 1
        self.idf = np.zeros(V, dtype=np.float32)
        for word, idx in self.vocab.items():
            self.idf[idx] = math.log((N + 1) / (df[word] + 1)) + 1
        self._fitted = True
        return self

    def transform(self, texts: list[str]) -> np.ndarray:
        if not self._fitted or self.idf is None:
            raise RuntimeError("Vectorizer not fitted")
        N, V = len(texts), len(self.vocab)
        matrix = np.zeros((N, V), dtype=np.float32)
        for i, text in enumerate(texts):
            feats = self._tokenize(text)
            tf = Counter(feats)
            for word, count in tf.items():
                if word in self.vocab:
                    matrix[i, self.vocab[word]] = (1 + math.log(count)) * self.idf[self.vocab[word]]
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return matrix / norms

    def get_feature_count(self) -> int:
        return len(self.vocab)


# ---------------------------------------------------------------------------
# Multi-class Logistic Regression (pure numpy)
# ---------------------------------------------------------------------------


class LogisticRegression:
    """Multi-class Logistic Regression with softmax and L2 regularization."""

    def __init__(self, lr: float = 0.01, n_iter: int = 200, l2: float = 0.01) -> None:
        self.lr = lr
        self.n_iter = n_iter
        self.l2 = l2
        self.weights: np.ndarray | None = None
        self.bias: np.ndarray | None = None
        self.classes: list[str] = []
        self._fitted = False

    def fit(self, X: np.ndarray, y: np.ndarray, classes: list[str]) -> LogisticRegression:
        N, V = X.shape
        K = len(classes)
        self.classes = classes
        self.weights = np.random.randn(V, K) * 0.01
        self.bias = np.zeros(K)
        prev_loss = float("inf")
        for iteration in range(self.n_iter):
            logits = X @ self.weights + self.bias
            exp_l = np.exp(logits - np.max(logits, axis=1, keepdims=True))
            probs = exp_l / np.sum(exp_l, axis=1, keepdims=True)
            loss = -np.mean(np.log(probs[np.arange(N), y] + 1e-15))
            loss += (self.l2 / 2) * np.sum(self.weights ** 2)
            grad = probs.copy()
            grad[np.arange(N), y] -= 1
            grad /= N
            self.weights -= self.lr * (X.T @ grad + self.l2 * self.weights)
            self.bias -= self.lr * np.sum(grad, axis=0)
            if abs(prev_loss - loss) < 1e-6:
                break
            prev_loss = loss
        self._fitted = True
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        if not self._fitted or self.weights is None or self.bias is None:
            raise RuntimeError("Model not fitted")
        logits = X @ self.weights + self.bias
        exp_l = np.exp(logits - np.max(logits, axis=1, keepdims=True))
        return exp_l / np.sum(exp_l, axis=1, keepdims=True)

    def predict(self, X: np.ndarray) -> list[int]:
        return list(np.argmax(self.predict_proba(X), axis=1))


# ---------------------------------------------------------------------------
# BehaviorClassifier
# ---------------------------------------------------------------------------


class BehaviorClassifier:
    """Behavior-Centric Classifier — keyword cold-start + trained ML modes."""

    def __init__(self, threshold: float = 0.9) -> None:
        self.threshold = threshold
        self.vectorizer = TfidfVectorizer(max_features=500)
        self.classifier = LogisticRegression(lr=0.01, n_iter=200)
        self._is_trained = False
        self._label_map: dict[str, int] = {}
        self._reverse_map: dict[int, str] = {}

    def classify(self, text: str) -> tuple[str, float]:
        if not text or not text.strip():
            return ("owner_decision", 0.0)
        if self._is_trained:
            return self._classify_ml(text)
        return self._classify_keyword(text)

    def classify_to_dept(self, text: str) -> tuple[str, str, float]:
        behavior, confidence = self.classify(text)
        return behavior, BEHAVIOR_DEPT_MAP.get(behavior, "ceo"), confidence

    def train(self, labeled_data: list[tuple[str, str]]) -> BehaviorClassifier:
        if not labeled_data:
            return self
        texts, labels = zip(*labeled_data)
        unique_labels = sorted(set(labels))
        self._label_map = {n: i for i, n in enumerate(unique_labels)}
        self._reverse_map = {i: n for n, i in self._label_map.items()}
        y = np.array([self._label_map[l] for l in labels], dtype=np.int32)
        aug_texts, aug_labels = list(texts), list(labels)
        for bname, kws in SEED_KEYWORDS.items():
            if bname in self._label_map:
                for kw in kws:
                    aug_texts.append(f"need to handle {kw}")
                    aug_labels.append(bname)
        self.vectorizer.fit(aug_texts)
        aug_y = np.array([self._label_map[l] for l in aug_labels], dtype=np.int32)
        X = self.vectorizer.transform(aug_texts)
        self.classifier.fit(X, aug_y, list(self._label_map.keys()))
        self._is_trained = True
        return self

    @property
    def is_trained(self) -> bool:
        return self._is_trained

    def save_model(self, path: str | Path) -> None:
        data = {"vectorizer": self.vectorizer, "classifier": self.classifier,
                "label_map": self._label_map, "reverse_map": self._reverse_map,
                "is_trained": self._is_trained}
        with open(path, "wb") as f:
            pickle.dump(data, f)

    def load_model(self, path: str | Path) -> BehaviorClassifier:
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.vectorizer = data["vectorizer"]
        self.classifier = data["classifier"]
        self._label_map = data["label_map"]
        self._reverse_map = data["reverse_map"]
        self._is_trained = data["is_trained"]
        return self

    def _classify_ml(self, text: str) -> tuple[str, float]:
        try:
            X = self.vectorizer.transform([text])
            probs = self.classifier.predict_proba(X)[0]
            best_idx = int(np.argmax(probs))
            return self._reverse_map.get(best_idx, "owner_decision"), float(probs[best_idx])
        except Exception:
            return self._classify_keyword(text)

    def _classify_keyword(self, text: str) -> tuple[str, float]:
        text_lower = text.lower()
        scores: dict[str, float] = {}
        for bname, kws in SEED_KEYWORDS.items():
            matches = sum(1 for kw in kws if kw.lower() in text_lower)
            if matches:
                scores[bname] = matches / max(len(kws), 1)
        if not scores:
            return ("owner_decision", 0.0)
        best = max(scores, key=scores.get)
        return best, min(scores[best] * 1.5, 0.95)


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

_default_classifier: BehaviorClassifier | None = None


def get_classifier() -> BehaviorClassifier:
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = BehaviorClassifier()
    return _default_classifier


def classify_behavior(text: str) -> tuple[str, str, float]:
    clf = get_classifier()
    return clf.classify_to_dept(text)
