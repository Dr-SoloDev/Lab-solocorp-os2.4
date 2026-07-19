"""Central Bus v0.6 — Behavior Classifier.

TF-IDF + Logistic Regression classifier for Behavior-Centric Routing.

Architecture
~~~~~~~~~~~~
- **Tier 0**: Behavior Classifier (fast path, <50ms)
- **Classifier**: TF-IDF vectorizer → Multi-class Logistic Regression (pure numpy)
- **Cold start**: Keyword heuristic until trained on enough labeled data
- **Confidence**: Calibrated via softmax probabilities, threshold ≥0.9

Usage::

    # Cold start (keyword-based)
    classifier = BehaviorClassifier()
    behavior_id, confidence = classifier.classify("I need a budget for Q3")

    # Train with labeled data
    classifier.train([
        ("I need budget approval for Q3", "budget_approval"),
        ("Fix the login page bug", "bug_fixing"),
    ])

    # Persist / Load
    classifier.save_model("classifier_model.pkl")
    classifier.load_model("classifier_model.pkl")
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


# ═══════════════════════════════════════════════════════════════════════
# Seed Keyword Data (from behavior_migration.py)
# Used for cold-start keyword heuristic matching
# ═══════════════════════════════════════════════════════════════════════

# Mapping: behavior_name -> list of trigger keywords
SEED_KEYWORDS: dict[str, list[str]] = {
    "vision_strategy": ["vision", "strategy", "mission", "direction", "goal", "objective", "strategic", "long-term", "กลยุทธ์", "วิสัยทัศน์", "เป้าหมาย", "ทิศทาง"],
    "owner_decision": ["final decision", "approve", "escalate", "owner", "authorize", "sign off", "decide", "อนุมัติ", "ตัดสินใจ", "owner"],
    "budget_approval": ["budget", "funding", "allocate", "resource", "งบประมาณ", "งบ", "จัดสรร", "ทุน", "approve budget"],
    "cost_analysis": ["cost", "roi", "profit", "revenue", "financial model", "forecast", "expense", "ต้นทุน", "กำไร", "รายได้", "วิเคราะห์การเงิน"],
    "campaign_management": ["campaign", "marketing", "advertising", "promotion", "ad", "แคมเปญ", "โฆษณา", "โปรโมท", "การตลาด"],
    "brand_strategy": ["brand", "branding", "positioning", "identity", "แบรนด์", "brand identity"],
    "content_production": ["content", "write", "caption", "copy", "blog", "post", "video", "script", "article", "คอนเทนต์", "เขียน", "แคปชั่น", "บทความ"],
    "pipeline_coordination": ["pipeline", "workflow", "orchestrate", "coordinate", "handoff", "cross", "ประสานงาน", "ส่งต่อ", "pipeline status"],
    "architecture_design": ["architecture", "system design", "schema", "central bus", "adr", "infrastructure", "สถาปัตยกรรม", "ออกแบบระบบ"],
    "routing_monitoring": ["routing", "route", "monitor", "health check", "watchdog", "circuit breaker", "เส้นทาง", "มอนิเตอร์", "เฝ้าระวัง"],
    "feature_definition": ["feature", "prd", "requirement", "user story", "product", "spec", "feature request", "ฟีเจอร์", "ความต้องการ"],
    "roadmap_planning": ["roadmap", "prioritize", "backlog", "release", "planning", "sprint", "โรดแมพ", "ลำดับความสำคัญ"],
    "backend_development": ["backend", "api", "database", "server", "microservice", "endpoint", "แบ็กเอนด์", "ฐานข้อมูล", "เซิร์ฟเวอร์"],
    "frontend_development": ["frontend", "ui code", "component", "react", "vue", "html", "css", "tailwind", "ui component"],
    "bug_fixing": ["bug", "fix", "error", "crash", "defect", "regression", "broken", "บั๊ก", "แก้", "พัง"],
    "visual_design": ["design system", "visual", "style guide", "figma", "ออกแบบ", "component library", "ui design"],
    "ux_research": ["ux", "user research", "usability", "wireframe", "user experience", "research", "วิจัย", "ผู้ใช้"],
    "qa_testing": ["test", "qa", "quality", "test case", "automation test", "testing", "ทดสอบ", "คุณภาพ"],
    "sales_deal": ["sales", "deal", "proposal", "close", "prospect", "pipeline deal", "ขาย", "ดีล", "เซลส์"],
    "customer_support": ["support", "customer", "ticket", "help", "issue", "service", "ซัพพอร์ต", "ลูกค้า", "ช่วย"],
    "legal_compliance": ["compliance", "regulatory", "pdpa", "gdpr", "regulation", "กฎหมาย", "compliant"],
    "contract_management": ["contract", "agreement", "nda", "mou", "legal", "document", "สัญญา", "นิติกรรม", "ข้อตกลง"],
    "smart_contract_defi": ["smart contract", "defi", "solana", "blockchain", "solidity", "anchor", "token", "crypto", "web3"],
    "network_operations": ["network", "cdn", "dns", "vpn", "load balancer", "bandwidth", "infrastructure", "เครือข่าย"],
    "security_incident": ["security", "threat", "vulnerability", "incident", "breach", "attack", "cyber", "ความปลอดภัย", "ภัยคุกคาม"],
    "behavioral_research": ["psychology", "behavior", "cognitive bias", "user behavior", "bias", "จิตวิทยา", "พฤติกรรม"],
}

# Map behavior_name -> primary_dept
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


# ═══════════════════════════════════════════════════════════════════════
# TF-IDF Vectorizer (pure numpy)
# ═══════════════════════════════════════════════════════════════════════


class TfidfVectorizer:
    """Simple TF-IDF vectorizer — word tokens + character 3-grams.

    Mirrors the approach from ``central_bus.semantic`` for consistency.
    """

    def __init__(self, max_features: int = 500) -> None:
        self.max_features = max_features
        self.vocab: dict[str, int] = {}
        self.idf: np.ndarray | None = None
        self._fitted = False

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Extract word tokens + character 3-grams for robust matching."""
        flat = text.lower()
        flat = re.sub(r"[^a-zก-๙0-9\s]", " ", flat)
        words = [t for t in flat.split() if len(t) > 1]
        clean = re.sub(r"\s", "", flat)
        ngrams = [
            clean[i:i+3]
            for i in range(len(clean) - 2)
            if len(clean[i:i+3]) == 3
        ]
        return words + ngrams

    def fit(self, texts: list[str]) -> TfidfVectorizer:
        """Build vocabulary and IDF from a list of texts."""
        all_feats: list[list[str]] = [self._tokenize(t) for t in texts]
        N = len(texts)

        # Build vocab from all features
        vocab_counter: Counter = Counter()
        for feats in all_feats:
            for t in feats:
                vocab_counter[t] += 1

        # Keep top max_features by frequency
        most_common = vocab_counter.most_common(self.max_features)
        self.vocab = {word: i for i, (word, _) in enumerate(most_common)}
        V = len(self.vocab)

        # Document frequency
        df = Counter()
        for feats in all_feats:
            for t in set(feats):
                if t in self.vocab:
                    df[t] += 1

        # IDF
        self.idf = np.zeros(V, dtype=np.float32)
        for word, idx in self.vocab.items():
            self.idf[idx] = math.log((N + 1) / (df[word] + 1)) + 1

        self._fitted = True
        log.debug("TF-IDF vocab size: %d", V)
        return self

    def transform(self, texts: list[str]) -> np.ndarray:
        """Transform texts to TF-IDF matrix (N x V)."""
        if not self._fitted or self.idf is None:
            raise RuntimeError("Vectorizer not fitted — call .fit() first")

        N = len(texts)
        V = len(self.vocab)
        matrix = np.zeros((N, V), dtype=np.float32)

        for i, text in enumerate(texts):
            feats = self._tokenize(text)
            tf = Counter(feats)
            for word, count in tf.items():
                if word in self.vocab:
                    idx = self.vocab[word]
                    matrix[i, idx] = (1 + math.log(count)) * self.idf[idx]

        # L2 normalize rows
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return matrix / norms

    def get_feature_count(self) -> int:
        return len(self.vocab)


# ═══════════════════════════════════════════════════════════════════════
# Multi-class Logistic Regression (pure numpy)
# Uses softmax + gradient descent for training
# ═══════════════════════════════════════════════════════════════════════


class LogisticRegression:
    """Multi-class Logistic Regression with softmax and L2 regularization.

    Implemented in pure numpy — no external ML dependency required.
    """

    def __init__(
        self,
        learning_rate: float = 0.01,
        n_iter: int = 200,
        l2_lambda: float = 0.01,
    ) -> None:
        self.learning_rate = learning_rate
        self.n_iter = n_iter
        self.l2_lambda = l2_lambda
        self.weights: np.ndarray | None = None
        self.bias: np.ndarray | None = None
        self.classes: list[str] = []
        self._fitted = False

    def fit(
        self,
        X: np.ndarray,
        y: np.ndarray,
        classes: list[str],
    ) -> LogisticRegression:
        """Fit multi-class logistic regression.

        Args:
            X: Training features (N x V)
            y: Target indices (N,) — integer labels
            classes: List of class names corresponding to indices
        """
        N, V = X.shape
        K = len(classes)
        self.classes = classes

        # Initialize weights
        self.weights = np.random.randn(V, K) * 0.01
        self.bias = np.zeros(K)

        # Gradient descent
        prev_loss = float("inf")
        for iteration in range(self.n_iter):
            # Forward pass: softmax
            logits = X @ self.weights + self.bias  # N x K
            exp_logits = np.exp(logits - np.max(logits, axis=1, keepdims=True))
            probs = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)

            # Cross-entropy loss with L2 regularization
            loss = -np.mean(np.log(probs[np.arange(N), y] + 1e-15))
            loss += (self.l2_lambda / 2) * np.sum(self.weights ** 2)

            # Backward pass
            grad_probs = probs.copy()
            grad_probs[np.arange(N), y] -= 1
            grad_probs /= N

            grad_weights = X.T @ grad_probs + self.l2_lambda * self.weights
            grad_bias = np.sum(grad_probs, axis=0)

            # Update
            self.weights -= self.learning_rate * grad_weights
            self.bias -= self.learning_rate * grad_bias

            # Convergence check
            if abs(prev_loss - loss) < 1e-6:
                log.debug("Converged at iteration %d (loss=%.6f)", iteration, loss)
                break
            prev_loss = loss

        self._fitted = True
        log.debug("LogisticRegression trained: %d classes, final loss=%.4f", K, prev_loss)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict class probabilities.

        Returns:
            N x K probability matrix
        """
        if not self._fitted or self.weights is None or self.bias is None:
            raise RuntimeError("Model not fitted — call .fit() first")

        logits = X @ self.weights + self.bias
        exp_logits = np.exp(logits - np.max(logits, axis=1, keepdims=True))
        return exp_logits / np.sum(exp_logits, axis=1, keepdims=True)

    def predict(self, X: np.ndarray) -> list[int]:
        """Predict class indices."""
        probs = self.predict_proba(X)
        return list(np.argmax(probs, axis=1))

    def predict_proba_single(self, x: np.ndarray) -> dict[str, float]:
        """Predict probabilities for a single sample.

        Returns:
            dict mapping class_name -> probability
        """
        probs = self.predict_proba(x.reshape(1, -1))[0]
        return {cls: float(prob) for cls, prob in zip(self.classes, probs)}


# ═══════════════════════════════════════════════════════════════════════
# BehaviorClassifier — Main Class
# ═══════════════════════════════════════════════════════════════════════


class BehaviorClassifier:
    """Behavior-Centric Classifier for SoloCorp OS routing.

    Two modes:
      1. **Trained (ML)**: TF-IDF + Logistic Regression — used after
         ``.train()`` has been called with labeled data.
      2. **Cold start (keyword heuristic)**: Keyword matching using
         seed keywords — used before training data is available.

    Confidence calibration:
      - Trained mode: softmax probability from Logistic Regression
      - Cold start: normalized keyword match score
      - Threshold: ≥0.9 → auto-route, <0.9 → fallback to Tiers 1-3
    """

    def __init__(self, threshold: float = 0.9) -> None:
        self.threshold = threshold
        self.vectorizer = TfidfVectorizer(max_features=500)
        self.classifier = LogisticRegression(learning_rate=0.01, n_iter=200)
        self._is_trained = False
        self._label_map: dict[str, int] = {}  # behavior_name -> int
        self._reverse_map: dict[int, str] = {}  # int -> behavior_name

    # ── Public API ─────────────────────────────────────────────────

    def classify(self, text: str) -> tuple[str, float]:
        """Classify a request text into a behavior.

        Returns:
            (behavior_name: str, confidence: float)
        """
        if not text or not text.strip():
            return self._default_fallback(), 0.0

        # Tier 1: ML classifier (if trained)
        if self._is_trained:
            return self._classify_ml(text)

        # Tier 2: Cold start — keyword heuristic
        return self._classify_keyword(text)

    def classify_to_dept(self, text: str) -> tuple[str, str, float]:
        """Classify and resolve to department.

        Returns:
            (behavior_name: str, department: str, confidence: float)
        """
        behavior, confidence = self.classify(text)
        dept = BEHAVIOR_DEPT_MAP.get(behavior, "ceo")
        return behavior, dept, confidence

    def train(
        self,
        labeled_data: list[tuple[str, str]],
    ) -> BehaviorClassifier:
        """Train the ML classifier on labeled data.

        Args:
            labeled_data: list of (text, behavior_name) pairs

        The classifier will switch from cold-start to ML mode
        after training.
        """
        if not labeled_data:
            log.warning("No training data provided — staying in cold-start mode")
            return self

        texts, labels = zip(*labeled_data)

        # Build label map
        unique_labels = sorted(set(labels))
        self._label_map = {name: i for i, name in enumerate(unique_labels)}
        self._reverse_map = {i: name for name, i in self._label_map.items()}
        y = np.array([self._label_map[l] for l in labels], dtype=np.int32)

        # Additional training data from seed keywords
        augmented_texts = list(texts)
        augmented_labels = list(labels)
        for behavior_name, keywords in SEED_KEYWORDS.items():
            if behavior_name in self._label_map:
                for kw in keywords:
                    augmented_texts.append(f"I need to handle {kw}")
                    augmented_labels.append(behavior_name)

        log.info(
            "Training classifier on %d samples (%d unique classes)",
            len(augmented_texts),
            len(unique_labels),
        )

        # Fit vectorizer
        self.vectorizer.fit(augmented_texts)

        # Build label map for augmented data
        augmented_y = np.array(
            [self._label_map[l] for l in augmented_labels],
            dtype=np.int32,
        )

        # Transform and train
        X = self.vectorizer.transform(augmented_texts)
        self.classifier.fit(X, augmented_y, list(self._label_map.keys()))

        self._is_trained = True
        log.info(
            "Classifier trained: %d features, %d classes",
            self.vectorizer.get_feature_count(),
            len(unique_labels),
        )

        return self

    @property
    def is_trained(self) -> bool:
        return self._is_trained

    # ── Persistence ─────────────────────────────────────────────────

    def save_model(self, path: str | Path) -> None:
        """Save the trained model to disk (pickle)."""
        data = {
            "vectorizer": self.vectorizer,
            "classifier": self.classifier,
            "label_map": self._label_map,
            "reverse_map": self._reverse_map,
            "is_trained": self._is_trained,
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)
        log.info("Model saved to %s", path)

    def load_model(self, path: str | Path) -> BehaviorClassifier:
        """Load a trained model from disk (pickle)."""
        with open(path, "rb") as f:
            data = pickle.load(f)

        self.vectorizer = data["vectorizer"]
        self.classifier = data["classifier"]
        self._label_map = data["label_map"]
        self._reverse_map = data["reverse_map"]
        self._is_trained = data["is_trained"]

        log.info(
            "Model loaded from %s (trained=%s, classes=%d)",
            path,
            self._is_trained,
            len(self._label_map),
        )
        return self

    # ── Internal: ML classification ─────────────────────────────────

    def _classify_ml(self, text: str) -> tuple[str, float]:
        """Classify using trained ML model."""
        try:
            X = self.vectorizer.transform([text])
            probs = self.classifier.predict_proba(X)[0]
            best_idx = int(np.argmax(probs))
            confidence = float(probs[best_idx])
            behavior = self._reverse_map.get(best_idx, self._default_fallback())
            return behavior, confidence
        except Exception as e:
            log.warning("ML classification failed: %s — falling back to keyword", e)
            return self._classify_keyword(text)

    # ── Internal: Keyword heuristic (cold start) ────────────────────

    def _classify_keyword(self, text: str) -> tuple[str, float]:
        """Cold-start classification using keyword matching.

        Counts keyword hits per behavior, normalizes by total keywords.
        Returns best match + normalized confidence score.
        """
        if not text or not text.strip():
            return self._default_fallback(), 0.0

        text_lower = text.lower()

        scores: dict[str, float] = {}
        for behavior_name, keywords in SEED_KEYWORDS.items():
            matches = 0
            for kw in keywords:
                if kw.lower() in text_lower:
                    matches += 1
            if matches > 0:
                # Normalize by keyword count — behaviors with fewer keywords
                # don't get penalized for having a concise list
                scores[behavior_name] = matches / max(len(keywords), 1)

        if not scores:
            return self._default_fallback(), 0.0

        # Find best match
        best_behavior = max(scores, key=scores.get)
        best_score = scores[best_behavior]

        # Normalize confidence: if score > 0.5, it's a strong match;
        # scale to 0.0-1.0 range
        confidence = min(best_score * 1.5, 0.95)

        return best_behavior, confidence

    def _default_fallback(self) -> str:
        """Default fallback behavior when nothing matches."""
        return "owner_decision"  # CEO handles unclear requests


# ═══════════════════════════════════════════════════════════════════════
# Convenience: global singleton
# ═══════════════════════════════════════════════════════════════════════

_default_classifier: BehaviorClassifier | None = None


def get_classifier() -> BehaviorClassifier:
    """Get or create the default BehaviorClassifier singleton."""
    global _default_classifier
    if _default_classifier is None:
        _default_classifier = BehaviorClassifier()
    return _default_classifier


def classify_behavior(text: str) -> tuple[str, str, float]:
    """Quick classification — returns (behavior, department, confidence).

    Convenience function for one-off use.
    """
    clf = get_classifier()
    return clf.classify_to_dept(text)
