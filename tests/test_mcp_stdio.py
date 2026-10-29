from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.asyncio
async def test_content_mcp_stdio_handshake_and_tool_call(tmp_path):
    env = os.environ.copy()
    env["SOLOCORP_BUS_ROOT"] = str(tmp_path / "central_bus")
    params = StdioServerParameters(
        command=str(ROOT / ".venv/bin/python3"),
        args=["-m", "solocorp_mcp.departments.content_mcp"],
        cwd=str(ROOT),
        env=env,
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            names = {tool.name for tool in listed.tools}
            assert "content_department_info" in names
            assert "create_content_draft" in names
            assert "design_audio_experience" in names
            assert "generate_voice_lipsync_prompt" in names
            assert "record_human_approval" in names
            assert "ingest_client_generated_artifact" in names
            result = await session.call_tool(
                "create_content_draft",
                {
                    "title": "stdio smoke",
                    "topic": "MCP department",
                    "target_audience": "ผู้สร้างระบบ",
                    "content_type": "social_post",
                },
            )
            ingest_result = await session.call_tool(
                "ingest_client_generated_artifact",
                {
                    "campaign_id": "stdio-client-pilot",
                    "artifact_type": "article",
                    "content": "## Hook\n\nA client-generated test.\n\n## Body\n\nStored without an LLM call.\n",
                    "source_references": ["https://research.example/stdio"],
                    "provenance": {
                        "client": "opencode",
                        "provider": "test-provider",
                        "model": "test-model",
                    },
                },
            )
            review_result = await session.call_tool(
                "review_publish_gate", {"campaign_id": "stdio-client-pilot"}
            )

    payload = json.loads(result.content[0].text)
    assert payload["status"] == "created"
    assert payload["path"].startswith("content/")
    ingested = json.loads(ingest_result.content[0].text)
    assert ingested["status"] == "client_generated"
    assert ingested["provenance_status"] == "client_supplied_unverified"
    review = json.loads(review_result.content[0].text)
    assert review["status"] == "review_required"
    assert review["publish_action"] == "blocked_until_human_approval"
