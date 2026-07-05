"""Tests for central_bus.facts — FactsService."""

from __future__ import annotations

import pytest
import pytest_asyncio

from central_bus.db import DbManager
from central_bus.facts import FactsService


@pytest_asyncio.fixture
async def db():
    d = DbManager(db_path=":memory:")
    await d.init()
    yield d
    await d.close()


@pytest_asyncio.fixture
async def facts(db):
    return FactsService(db)


# ── get_fact / set_fact ─────────────────────────────────────────


class TestGetSetFact:
    async def test_get_nonexistent(self, facts: FactsService) -> None:
        assert await facts.get_fact("no.such.key") is None

    async def test_set_and_get(self, facts: FactsService) -> None:
        result = await facts.set_fact("agent.status.changful", "active")
        assert result["key"] == "agent.status.changful"
        assert result["value"] == "active"
        assert result["version"] == 1

        fetched = await facts.get_fact("agent.status.changful")
        assert fetched is not None
        assert fetched["value"] == "active"
        assert fetched["version"] == 1

    async def test_set_with_dict_value(self, facts: FactsService) -> None:
        val = {"role": "engineer", "department": "engineering"}
        await facts.set_fact("agent.profile.changful", val)
        fetched = await facts.get_fact("agent.profile.changful")
        assert fetched["value"] == val

    async def test_set_with_metadata(self, facts: FactsService) -> None:
        meta = {"source": "onboarding", "ttl": 3600}
        await facts.set_fact("agent.status.bob", "idle", metadata=meta)
        fetched = await facts.get_fact("agent.status.bob")
        assert fetched["metadata"] == meta

    async def test_version_increment(self, facts: FactsService) -> None:
        await facts.set_fact("counter.test", 1)
        assert (await facts.get_fact("counter.test"))["version"] == 1
        await facts.set_fact("counter.test", 2)
        assert (await facts.get_fact("counter.test"))["version"] == 2
        assert (await facts.get_fact("counter.test"))["value"] == 2


# ── list_facts ──────────────────────────────────────────────────


class TestListFacts:
    async def test_list_all(self, facts: FactsService) -> None:
        await facts.set_fact("a.one", 1)
        await facts.set_fact("b.two", 2)
        await facts.set_fact("c.three", 3)
        all_facts = await facts.list_facts()
        assert len(all_facts) == 3

    async def test_list_with_prefix(self, facts: FactsService) -> None:
        await facts.set_fact("agent.status.changful", "active")
        await facts.set_fact("agent.status.bob", "idle")
        await facts.set_fact("routing.rule.001", "engineering")
        agent_facts = await facts.list_facts(prefix="agent.status.*")
        assert len(agent_facts) == 2
        keys = {f["key"] for f in agent_facts}
        assert keys == {"agent.status.changful", "agent.status.bob"}

    async def test_list_limit(self, facts: FactsService) -> None:
        for i in range(10):
            await facts.set_fact(f"key.{i}", i)
        limited = await facts.list_facts(limit=3)
        assert len(limited) == 3


# ── delete_fact ─────────────────────────────────────────────────


class TestDeleteFact:
    async def test_delete_existing(self, facts: FactsService) -> None:
        await facts.set_fact("temp.key", "value")
        assert await facts.get_fact("temp.key") is not None
        deleted = await facts.delete_fact("temp.key")
        assert deleted is True
        assert await facts.get_fact("temp.key") is None

    async def test_delete_nonexistent(self, facts: FactsService) -> None:
        deleted = await facts.delete_fact("no.such.key")
        assert deleted is False


# ── count_facts ─────────────────────────────────────────────────


class TestCountFacts:
    async def test_count(self, facts: FactsService) -> None:
        assert await facts.count_facts() == 0
        await facts.set_fact("a", 1)
        await facts.set_fact("b", 2)
        assert await facts.count_facts() == 2
        await facts.delete_fact("a")
        assert await facts.count_facts() == 1
