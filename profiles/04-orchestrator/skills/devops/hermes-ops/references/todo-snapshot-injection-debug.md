# todo_snapshot Injection Bug — Debugging Trace

**Session:** 2026-06-18, SoloCorp OS Sprint A → context compaction cross-contamination
**Root cause:** `conversation_compression.py` line 501–503 in Hermes v0.16.0
**Fix:** See `SKILL.md` Part C5

## Chain of Events

1. Session A (SoloCorp OS Sprint A) was actively running with task list:
   ```
   [>] s3. [พี่ทรงศักดิ์] Sprint A Build (in_progress)
   [ ] s4. [คุณวุฒิ] ตรวจสอบ + สรุป (pending)
   ...
   ```

2. Context compaction triggered — `compress_context()` in `conversation_compression.py` called `agent.context_compressor.compress(messages)`.

3. Compressor returned `compressed` = head messages + summary + tail messages, ending with `_SUMMARY_END_MARKER`:
   ```
   --- END OF CONTEXT SUMMARY — respond to the message below, not the summary above ---
   ```

4. **The bug:** After compression, lines 501–503 appended:
   ```python
   todo_snapshot = agent._todo_store.format_for_injection()
   if todo_snapshot:
       compressed.append({"role": "user", "content": todo_snapshot})
   ```

   This added a `"user"` message **after** the summary end marker.

5. System prompt directive says: *"Respond ONLY to the latest user message that appears AFTER this summary"* — the todo_snapshot with `role="user"` matches this exactly.

6. The model sees the SoloCorp task list as the latest user instruction → resumes/resurrects stale tasks.

## Subsequent Red Herring

When the user then asked: *"เปิดโปรเจกต์ Secondhand POS มาหน่อย"* (which was actually a fragment from a previous session about Secondhand POS, not a new command), and the model already had the stale task list as the latest "user" message, the combination caused the model to:

- See the Secondhand POS text as the active instruction
- Abandon the SoloCorp Sprint A work
- Jump to the Secondhand POS project

## Fix Verification Checklist

After applying the fix:

- [ ] `conversation_compression.py` line 501–503 uses `role="assistant"` (not `"user"`)
- [ ] Content has explicit `[Reference only — ...]` disclaimer
- [ ] Metadata `_compressed_summary: True` is present on the injected message
- [ ] Python syntax validates: `python3 -c "ast.parse(open('agent/conversation_compression.py').read())"`
- [ ] No import needed for `COMPRESSED_SUMMARY_METADATA_KEY` (use string literal `"_compressed_summary"`)
- [ ] `_compressed_summary` starts with underscore (wire sanitizer strips it)

## Related Hermes Source Files

| File | Role |
|------|------|
| `agent/conversation_compression.py` | Orchestration — where todo_snapshot is injected |
| `agent/context_compressor.py` | LLM-based summarisation — produces the compressed messages |
| `agent/context_compressor.py::SUMMARY_PREFIX` | The `[CONTEXT COMPACTION — REFERENCE ONLY]` preamble |
| `agent/context_compressor.py::_SUMMARY_END_MARKER` | The `--- END OF CONTEXT SUMMARY ---` marker |
| `agent/transports/chat_completions.py::convert_messages` | Wire sanitizer that strips underscore-prefixed keys |
