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
            result = await session.call_tool(
                "create_content_draft",
                {
                    "title": "stdio smoke",
                    "topic": "MCP department",
                    "target_audience": "ผู้สร้างระบบ",
                    "content_type": "social_post",
                },
            )

    payload = json.loads(result.content[0].text)
    assert payload["status"] == "created"
    assert payload["path"].startswith("content/")
