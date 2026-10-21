"""Regression test — aiosqlite thread ต้องเป็น daemon

**Bug (21 ต.ค. 2569, deep health check):** `aiosqlite` เปิด connection thread
แบบ non-daemon → interpreter รอ thread นี้ตอน exit → pytest/โปรแกรม **ค้าง**
แม้เทสต์ผ่านหมด → CI ต้องรอจน timeout

**ทำไมเป็นบั๊กที่หลุดสายตา:** เทสต์ผ่าน 100% · exit code ถูก · แต่ process ไม่จบ
จึงไม่เคยโดนจับในรอบที่รันในเครื่อง (ที่มี aiosqlite เวอร์ชันใหม่กว่า)

**โครงสร้างต่างกันตามเวอร์ชัน:**
  aiosqlite >= 0.21 → Connection ห่อ `_thread` (Thread อยู่ข้างใน)
  aiosqlite <  0.21 → Connection สืบทอด `Thread` ตรง ๆ
→ fix ต้องตั้ง daemon ให้ตัวที่เป็น Thread จริงเสมอ
"""
from __future__ import annotations

import asyncio
import threading

import pytest

from central_bus.db import DbManager, open_connection


def _thread_of(conn) -> threading.Thread:
    """ดึง Thread จริง — รองรับทั้ง 2 โครงสร้าง"""
    return getattr(conn, "_thread", conn)


class TestAiosqliteDaemonThread:
    @pytest.mark.asyncio
    async def test_open_connection_thread_is_daemon(self, tmp_path):
        """connection ที่เปิดผ่าน open_connection() ต้องเป็น daemon"""
        conn = await open_connection(tmp_path / "t.db")
        try:
            assert _thread_of(conn).daemon is True, (
                "aiosqlite connection thread ต้องเป็น daemon "
                "(ไม่งั้น interpreter รอมันตอน exit → CI hang)"
            )
        finally:
            await conn.close()

    @pytest.mark.asyncio
    async def test_db_manager_connection_thread_is_daemon(self, tmp_path):
        """DbManager.init() ต้องได้ thread ที่เป็น daemon"""
        mgr = DbManager(db_path=str(tmp_path / "bus.db"))
        await mgr.init()
        try:
            assert mgr._conn is not None
            assert _thread_of(mgr._conn).daemon is True
        finally:
            await mgr.close()

    def test_no_non_daemon_connection_threads_left(self, tmp_path):
        """หลังเปิด+ปิด connection ต้องไม่เหลือ non-daemon thread ค้าง"""

        async def run():
            conn = await open_connection(tmp_path / "t2.db")
            await conn.execute("CREATE TABLE IF NOT EXISTS x (a int)")
            await conn.commit()
            await conn.close()

        before = {t.ident for t in threading.enumerate()}
        asyncio.run(run())

        leftover = [
            t for t in threading.enumerate()
            if t.ident not in before and not t.daemon and t.is_alive()
        ]
        assert not leftover, f"เหลือ non-daemon thread ค้าง: {leftover}"
