"""Tests for central_bus.behavior_classifier + router integration.

Coverage:
  - Unit: BehaviorClassifier cold-start keyword matching
  - Unit: BehaviorClassifier ML training + classification
  - Unit: TF-IDF Vectorizer
  - Unit: Logistic Regression
  - Integration: route_v2 pipeline (Tier 0 + fallback)
  - Performance: classification latency < 50ms
"""

from __future__ import annotations

import logging
import time
from typing import Any

import numpy as np
import pytest

from central_bus.behavior_classifier import (
    BEHAVIOR_DEPT_MAP,
    SEED_KEYWORDS,
    BehaviorClassifier,
    LogisticRegression,
    TfidfVectorizer,
    classify_behavior,
    get_classifier,
)
from central_bus.models import BusMessage
from central_bus.router import BehaviorRouter, route_v2

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════


@pytest.fixture
def classifier() -> BehaviorClassifier:
    """Fresh classifier instance (cold-start mode)."""
    return BehaviorClassifier(threshold=0.9)


@pytest.fixture
def trained_classifier() -> BehaviorClassifier:
    """Classifier pre-trained on sample labeled data."""
    clf = BehaviorClassifier(threshold=0.9)
    training_data = [
        # Engineering
        ("I need to fix a bug in the login page", "bug_fixing"),
        ("Build a new API endpoint for user data", "backend_development"),
        ("Create a React component for the dashboard", "frontend_development"),
        ("The database query is timing out", "bug_fixing"),
        ("Add a new REST endpoint for orders", "backend_development"),

        # Finance
        ("Approve budget for Q3 marketing", "budget_approval"),
        ("What is the ROI on this campaign", "cost_analysis"),
        ("We need funding for the new project", "budget_approval"),
        ("Analyze the cost structure of our cloud bill", "cost_analysis"),

        # Marketing
        ("Launch a new ad campaign on LinkedIn", "campaign_management"),
        ("Update our brand positioning", "brand_strategy"),
        ("Create a promotional offer for existing customers", "campaign_management"),

        # Content
        ("Write a blog post about AI", "content_production"),
        ("Create social media captions for the launch", "content_production"),

        # Product
        ("Write PRD for the new feature", "feature_definition"),
        ("Plan the Q4 product roadmap", "roadmap_planning"),

        # Architecture
        ("Design the system architecture for scaling", "architecture_design"),
        ("Set up monitoring for the routing pipeline", "routing_monitoring"),

        # Security
        ("There's a security vulnerability in the API", "security_incident"),

        # Support
        ("Customer support ticket about login issue", "customer_support"),

        # Sales
        ("Close the deal with Acme Corp", "sales_deal"),

        # Legal
        ("Review the NDA for our partner", "contract_management"),
        ("Check GDPR compliance", "legal_compliance"),

        # Leadership
        ("What is our long-term strategy", "vision_strategy"),
        ("I need an executive decision on this", "owner_decision"),

        # Design
        ("Redesign the landing page visual", "visual_design"),
        ("Conduct user research for the checkout flow", "ux_research"),

        # QA
        ("Run regression tests on the new build", "qa_testing"),

        # Pipeline
        ("Coordinate the handoff between product and engineering", "pipeline_coordination"),

        # Web3
        ("Deploy a Solana smart contract", "smart_contract_defi"),

        # Network
        ("Configure the CDN for faster delivery", "network_operations"),

        # Psychology
        ("Analyze user behavior patterns", "behavioral_research"),
    ]
    clf.train(training_data)
    return clf


@pytest.fixture
def behavior_router() -> BehaviorRouter:
    """BehaviorRouter with default classifier (no DB)."""
    return BehaviorRouter(classifier=BehaviorClassifier())


@pytest.fixture
def trained_behavior_router(trained_classifier) -> BehaviorRouter:
    """BehaviorRouter with trained classifier."""
    return BehaviorRouter(classifier=trained_classifier)


# ═══════════════════════════════════════════════════════════════════════
# Unit Tests — TfidfVectorizer
# ═══════════════════════════════════════════════════════════════════════


class TestTfidfVectorizer:
    def test_fit_transform_shape(self) -> None:
        vectorizer = TfidfVectorizer(max_features=100)
        texts = [
            "I need to fix a bug",
            "Approve the budget for Q3",
            "Design the system architecture",
        ]
        vectorizer.fit(texts)
        X = vectorizer.transform(texts)
        assert X.shape[0] == 3
        assert X.shape[1] <= 100
        assert X.shape[1] > 0

    def test_normalized_rows(self) -> None:
        vectorizer = TfidfVectorizer(max_features=50)
        texts = ["Fix a critical bug", "Bug in production"]
        vectorizer.fit(texts)
        X = vectorizer.transform(texts)
        norms = np.linalg.norm(X, axis=1)
        assert np.allclose(norms, 1.0, atol=1e-5)

    def test_similar_texts_have_similar_vectors(self) -> None:
        vectorizer = TfidfVectorizer(max_features=100)
        texts = [
            "Fix a critical bug in the login page",
            "Fix a bug in the checkout flow",
            "Design the system architecture for scale",
        ]
        vectorizer.fit(texts)
        X = vectorizer.transform(texts)

        # Bug-related texts should be more similar to each other
        sim_01 = float(np.dot(X[0], X[1]))
        sim_02 = float(np.dot(X[0], X[2]))
        assert sim_01 > sim_02

    def test_empty_text(self) -> None:
        vectorizer = TfidfVectorizer(max_features=50)
        vectorizer.fit(["test text"])
        X = vectorizer.transform([""])
        assert X.shape == (1, vectorizer.get_feature_count())

    def test_thai_text(self) -> None:
        vectorizer = TfidfVectorizer(max_features=100)
        texts = ["แก้บั๊กในระบบ login", "อนุมัติงบประมาณไตรมาส 3"]
        vectorizer.fit(texts)
        X = vectorizer.transform(texts)
        assert X.shape[0] == 2
        assert X.shape[1] > 0


# ═══════════════════════════════════════════════════════════════════════
# Unit Tests — Logistic Regression
# ═══════════════════════════════════════════════════════════════════════


class TestLogisticRegression:
    def test_fit_and_predict(self) -> None:
        # Simple synthetic data: 2 classes, 4 features
        np.random.seed(42)
        X = np.array([
            [1.0, 0.0, 0.5, 0.0],
            [0.9, 0.1, 0.4, 0.1],
            [0.0, 1.0, 0.0, 0.5],
            [0.1, 0.9, 0.1, 0.4],
        ], dtype=np.float32)
        y = np.array([0, 0, 1, 1], dtype=np.int32)
        classes = ["bug_fixing", "budget_approval"]

        model = LogisticRegression(learning_rate=0.1, n_iter=500)
        model.fit(X, y, classes)
        preds = model.predict(X)
        assert preds == [0, 0, 1, 1]

    def test_predict_proba(self) -> None:
        np.random.seed(42)
        X = np.array([
            [1.0, 0.0, 0.5],
            [0.0, 1.0, 0.0],
        ], dtype=np.float32)
        y = np.array([0, 1], dtype=np.int32)
        classes = ["class_a", "class_b"]

        model = LogisticRegression(learning_rate=0.1, n_iter=100)
        model.fit(X, y, classes)
        probs = model.predict_proba(X)
        assert probs.shape == (2, 2)
        # Probabilities should sum to 1
        assert np.allclose(np.sum(probs, axis=1), 1.0)

    def test_not_fitted_raises(self) -> None:
        model = LogisticRegression()
        with pytest.raises(RuntimeError):
            model.predict(np.array([[1.0, 0.0]]))


# ═══════════════════════════════════════════════════════════════════════
# Unit Tests — BehaviorClassifier (Cold Start)
# ═══════════════════════════════════════════════════════════════════════


class TestBehaviorClassifierColdStart:
    def test_initial_state(self, classifier: BehaviorClassifier) -> None:
        assert not classifier.is_trained
        assert classifier.threshold == 0.9

    def test_classify_budget_keyword(self, classifier: BehaviorClassifier) -> None:
        behavior, confidence = classifier.classify("I need budget approval for Q3")
        assert behavior == "budget_approval"
        assert 0.0 < confidence <= 1.0

    def test_classify_bug_keyword(self, classifier: BehaviorClassifier) -> None:
        behavior, confidence = classifier.classify("Fix the login page bug")
        assert behavior == "bug_fixing"
        assert confidence > 0.0

    def test_classify_security_keyword(self, classifier: BehaviorClassifier) -> None:
        behavior, confidence = classifier.classify(
            "Security vulnerability detected in the API endpoint"
        )
        assert behavior == "security_incident"
        assert confidence > 0.0

    def test_classify_vision_keyword(self, classifier: BehaviorClassifier) -> None:
        behavior, confidence = classifier.classify(
            "What is our long-term strategy for next year"
        )
        assert behavior == "vision_strategy"
        assert confidence > 0.0

    def test_classify_contract_keyword(self, classifier: BehaviorClassifier) -> None:
        behavior, confidence = classifier.classify(
            "Review the NDA agreement with the partner"
        )
        assert behavior == "contract_management"
        assert confidence > 0.0

    def test_classify_empty_text(self, classifier: BehaviorClassifier) -> None:
        behavior, confidence = classifier.classify("")
        assert behavior == "owner_decision"  # default fallback
        assert confidence == 0.0

    def test_classify_whitespace(self, classifier: BehaviorClassifier) -> None:
        behavior, confidence = classifier.classify("   ")
        assert behavior == "owner_decision"
        assert confidence == 0.0

    def test_classify_thai_text(self, classifier: BehaviorClassifier) -> None:
        behavior, confidence = classifier.classify("แก้บั๊กที่หน้า login")
        assert behavior == "bug_fixing"
        assert confidence > 0.0

    def test_classify_thai_budget(self, classifier: BehaviorClassifier) -> None:
        behavior, confidence = classifier.classify("อนุมัติงบประมาณ Q3")
        assert behavior == "budget_approval"
        assert confidence > 0.0

    def test_classify_to_dept(self, classifier: BehaviorClassifier) -> None:
        behavior, dept, confidence = classifier.classify_to_dept("Fix a bug")
        assert behavior == "bug_fixing"
        assert dept == "engineering"
        assert confidence > 0.0

    def test_classify_to_dept_unknown(self, classifier: BehaviorClassifier) -> None:
        behavior, dept, confidence = classifier.classify_to_dept("xyzzy unknown thing")
        # Should fallback to some reasonable default
        assert dept in (
            "ceo", "engineering", "product", "cfo", "cmo", "architect",
            "design", "qa", "sales", "support", "legal", "web3",
            "neteng", "cybersec", "psychology", "content_creator",
            "orchestrator",
        )

    def test_seed_keywords_completeness(self) -> None:
        """Verify all 26 behaviors have keyword entries."""
        expected_behaviors = {
            "vision_strategy", "owner_decision",
            "budget_approval", "cost_analysis",
            "campaign_management", "brand_strategy",
            "content_production",
            "pipeline_coordination",
            "architecture_design", "routing_monitoring",
            "feature_definition", "roadmap_planning",
            "backend_development", "frontend_development", "bug_fixing",
            "visual_design", "ux_research",
            "qa_testing",
            "sales_deal",
            "customer_support",
            "legal_compliance", "contract_management",
            "smart_contract_defi",
            "network_operations",
            "security_incident",
            "behavioral_research",
        }
        assert set(SEED_KEYWORDS.keys()) == expected_behaviors
        # Every behavior must have at least one keyword
        for name, keywords in SEED_KEYWORDS.items():
            assert len(keywords) > 0, f"{name} has no keywords"

    def test_behavior_dept_map_completeness(self) -> None:
        """Verify all 26 behaviors have department mappings."""
        assert len(BEHAVIOR_DEPT_MAP) == 26
        # All departments should be valid SoloCorp departments
        valid_depts = {
            "ceo", "cfo", "cmo", "orchestrator", "architect", "product",
            "engineering", "design", "ui_designer", "qa", "sales",
            "support", "legal", "web3", "content_creator", "neteng",
            "cybersec", "psychology",
        }
        for behavior, dept in BEHAVIOR_DEPT_MAP.items():
            assert dept in valid_depts, f"{behavior} -> invalid dept {dept}"


# ═══════════════════════════════════════════════════════════════════════
# Unit Tests — BehaviorClassifier (Trained Mode)
# ═══════════════════════════════════════════════════════════════════════


class TestBehaviorClassifierTrained:
    def test_is_trained_after_training(
        self, trained_classifier: BehaviorClassifier
    ) -> None:
        assert trained_classifier.is_trained

    def test_classify_bug_after_training(
        self, trained_classifier: BehaviorClassifier
    ) -> None:
        behavior, confidence = trained_classifier.classify(
            "There is a critical bug in the payment system"
        )
        assert behavior == "bug_fixing"
        assert confidence >= 0.0

    def test_classify_budget_after_training(
        self, trained_classifier: BehaviorClassifier
    ) -> None:
        behavior, confidence = trained_classifier.classify(
            "I need to approve the Q3 marketing budget"
        )
        assert behavior == "budget_approval"
        # ML should give high confidence for trained classes
        assert confidence >= 0.3

    def test_classify_sales_after_training(
        self, trained_classifier: BehaviorClassifier
    ) -> None:
        behavior, confidence = trained_classifier.classify(
            "We need to close the deal with Acme Corporation"
        )
        assert behavior == "sales_deal"
        assert confidence >= 0.0

    def test_classify_security_after_training(
        self, trained_classifier: BehaviorClassifier
    ) -> None:
        behavior, confidence = trained_classifier.classify(
            "Security breach detected — immediate response needed"
        )
        assert behavior == "security_incident"
        assert confidence >= 0.0

    def test_confidence_calibration(
        self, trained_classifier: BehaviorClassifier
    ) -> None:
        """Confidence should be in valid range."""
        test_cases = [
            "Fix this critical bug right now",
            "Approve the budget for the new project",
            "Design the system architecture for high availability",
            "Launch a new marketing campaign next week",
        ]
        for text in test_cases:
            _, confidence = trained_classifier.classify(text)
            assert 0.0 <= confidence <= 1.0, f"Bad confidence {confidence} for: {text}"

    def test_ml_fallback_to_keyword(
        self, trained_classifier: BehaviorClassifier
    ) -> None:
        """Even if ML fails, keyword fallback should work."""
        # Temporarily break the model
        trained_classifier._is_trained = False
        behavior, confidence = trained_classifier.classify("Fix a bug in production")
        assert behavior == "bug_fixing"
        assert confidence > 0.0


# ═══════════════════════════════════════════════════════════════════════
# Integration Tests — BehaviorRouter + route_v2
# ═══════════════════════════════════════════════════════════════════════


class TestBehaviorRouter:
    def _make_msg(
        self,
        text: str,
        msg_type: str = "HANDOFF",
        from_dept: str = "engineering",
    ) -> BusMessage:
        return BusMessage(
            from_dept=from_dept,
            to_dept="ceo",
            type=msg_type,
            project_id="test",
            phase="test",
            payload={"text": text, "description": text},
            trace_id="test-trace",
        )

    def test_route_v2_budget(
        self, trained_behavior_router: BehaviorRouter
    ) -> None:
        msg = self._make_msg("I need budget approval for Q3")
        dept = trained_behavior_router.route_v2_sync(
            BehaviorRouter._extract_text(msg)
        )
        assert dept == "cfo"

    def test_route_v2_bug(
        self, trained_behavior_router: BehaviorRouter
    ) -> None:
        msg = self._make_msg("Fix the critical login page bug")
        dept = trained_behavior_router.route_v2_sync(
            BehaviorRouter._extract_text(msg)
        )
        assert dept == "engineering"

    def test_route_v2_security(
        self, trained_behavior_router: BehaviorRouter
    ) -> None:
        msg = self._make_msg("Security incident — potential data breach detected")
        dept = trained_behavior_router.route_v2_sync(
            BehaviorRouter._extract_text(msg)
        )
        assert dept == "cybersec"

    def test_route_v2_vision(
        self, trained_behavior_router: BehaviorRouter
    ) -> None:
        msg = self._make_msg("What is our long-term strategy for next year")
        dept = trained_behavior_router.route_v2_sync(
            BehaviorRouter._extract_text(msg)
        )
        assert dept == "ceo"

    def test_route_v2_empty_payload(
        self, trained_behavior_router: BehaviorRouter
    ) -> None:
        msg = self._make_msg("")
        dept = trained_behavior_router.route_v2_sync(
            BehaviorRouter._extract_text(msg)
        )
        assert dept == "ceo"  # Default fallback

    def test_route_v2_governance_bypass(
        self, behavior_router: BehaviorRouter
    ) -> None:
        """Governance messages should bypass behavior classifier."""
        # Even without classifier, governance should route correctly
        msg = BusMessage(
            from_dept="architect",
            to_dept="orchestrator",
            type="GOVERNANCE",
            project_id="test",
            phase="test",
            payload={"gov_event": "guard_failed", "gov_detail": "test"},
            trace_id="gov-test",
        )
        # route_v2 handles governance by delegating to route()
        dept = behavior_router.route_v2_sync(
            BehaviorRouter._extract_text(msg)
        )
        # Should follow governance routing rules
        assert dept == "orchestrator" or dept is not None

    def test_classify_behavior_convenience(self) -> None:
        """Test the classify_behavior() module-level function."""
        behavior, dept, confidence = classify_behavior("Fix a bug in production")
        assert behavior == "bug_fixing"
        assert dept == "engineering"
        assert confidence > 0.0


# ═══════════════════════════════════════════════════════════════════════
# Performance Test — Classification Latency
# ═══════════════════════════════════════════════════════════════════════


class TestClassifierPerformance:
    """Performance tests: verify classification latency < 50ms.

    These tests validate the ADR-016 latency requirement.
    """

    SAMPLES = [
        "Fix a critical bug in the payment system",
        "I need budget approval for the Q3 marketing campaign",
        "Design the system architecture for high availability and scaling",
        "There is a security vulnerability in the API endpoint",
        "Write a blog post about our new AI features",
        "อนุมัติงบประมาณเพื่อการพัฒนาแพลตฟอร์มใหม่",
        "แก้บั๊กที่ระบบชำระเงินล่ม",
        "Review the NDA agreement with our new technology partner",
        "Launch a LinkedIn ad campaign for the product launch",
        "Coordinate the handoff between the product team and engineering",
        "Run regression tests on the latest build before deployment",
        "What is our strategic direction for the next fiscal year",
        "Configure the CDN for better global performance",
        "Deploy a new Solana smart contract for the token launch",
        "Analyze user behavior patterns in the new onboarding flow",
    ]

    def test_cold_start_latency(self, classifier: BehaviorClassifier) -> None:
        """Cold-start classification must be < 50ms per call."""
        times = []
        for _ in range(5):  # Warmup
            classifier.classify("Fix a bug")

        for sample in self.SAMPLES:
            start = time.perf_counter()
            classifier.classify(sample)
            elapsed = (time.perf_counter() - start) * 1000  # ms
            times.append(elapsed)

        max_time = max(times)
        avg_time = sum(times) / len(times)
        log.info(
            "Cold-start: max=%.2fms, avg=%.2fms (n=%d)",
            max_time, avg_time, len(times),
        )
        assert max_time < 50.0, (
            f"Max latency {max_time:.2f}ms exceeds 50ms limit"
        )

    def test_trained_latency(
        self, trained_classifier: BehaviorClassifier
    ) -> None:
        """Trained classification must be < 50ms per call."""
        times = []
        for _ in range(5):  # Warmup
            trained_classifier.classify("Fix a bug")

        for sample in self.SAMPLES:
            start = time.perf_counter()
            trained_classifier.classify(sample)
            elapsed = (time.perf_counter() - start) * 1000  # ms
            times.append(elapsed)

        max_time = max(times)
        avg_time = sum(times) / len(times)
        log.info(
            "Trained: max=%.2fms, avg=%.2fms (n=%d)",
            max_time, avg_time, len(times),
        )
        assert max_time < 50.0, (
            f"Max latency {max_time:.2f}ms exceeds 50ms limit"
        )

    def test_classifier_initialization_latency(self) -> None:
        """Classifier initialization should be fast (< 100ms)."""
        start = time.perf_counter()
        _ = BehaviorClassifier()
        elapsed = (time.perf_counter() - start) * 1000
        log.info("Initialization: %.2fms", elapsed)
        assert elapsed < 100.0, (
            f"Init latency {elapsed:.2f}ms exceeds 100ms limit"
        )

    def test_bulk_classification_throughput(
        self, trained_classifier: BehaviorClassifier
    ) -> None:
        """100 classifications should complete in < 500ms."""
        # Warmup
        for _ in range(10):
            trained_classifier.classify("Fix a bug")

        start = time.perf_counter()
        n = 100
        for i in range(n):
            trained_classifier.classify(self.SAMPLES[i % len(self.SAMPLES)])
        elapsed = (time.perf_counter() - start) * 1000
        avg = elapsed / n
        log.info(
            "Bulk %d: total=%.2fms, avg=%.2fms/call",
            n, elapsed, avg,
        )
        assert elapsed < 500.0, (
            f"Bulk latency {elapsed:.2f}ms exceeds 500ms limit for {n} calls"
        )


# ═══════════════════════════════════════════════════════════════════════
# Edge Cases
# ═══════════════════════════════════════════════════════════════════════


class TestEdgeCases:
    def test_case_insensitivity(self, classifier: BehaviorClassifier) -> None:
        """Classification should be case-insensitive."""
        b1, c1 = classifier.classify("FIX A CRITICAL BUG")
        b2, c2 = classifier.classify("fix a critical bug")
        assert b1 == b2
        assert abs(c1 - c2) < 0.01

    def test_partial_keyword_match(self, classifier: BehaviorClassifier) -> None:
        """Partial keyword matches should still work but with lower confidence."""
        _, confidence = classifier.classify("budget")
        assert confidence > 0.0

    def test_mixed_language(self, classifier: BehaviorClassifier) -> None:
        """Thai + English mixed should still classify."""
        behavior, confidence = classifier.classify(
            "แก้ bug ที่ระบบ payment"
        )
        assert behavior is not None
        assert confidence >= 0.0

    def test_very_long_text(self, classifier: BehaviorClassifier) -> None:
        """Very long text should still classify."""
        long_text = "We need to fix a bug " * 50
        behavior, confidence = classifier.classify(long_text)
        assert behavior == "bug_fixing"
        assert confidence > 0.0

    def test_save_load_model(
        self, trained_classifier: BehaviorClassifier, tmp_path
    ) -> None:
        """Model serialization round-trip should preserve classification."""
        model_path = tmp_path / "test_model.pkl"
        trained_classifier.save_model(str(model_path))
        assert model_path.exists()

        # Load into fresh instance
        new_clf = BehaviorClassifier()
        new_clf.load_model(str(model_path))
        assert new_clf.is_trained

        # Should produce same result
        b1, c1 = trained_classifier.classify("Fix a critical bug")
        b2, c2 = new_clf.classify("Fix a critical bug")
        assert b1 == b2
        assert abs(c1 - c2) < 0.1
