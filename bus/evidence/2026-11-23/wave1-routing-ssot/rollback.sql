-- ADR-040 Wave 1 — rollback for the live seed on 2026-11-23
-- Removes ONLY the 22 rows inserted by the seed run, then the 002 migration record.
-- Live DB uses the legacy schema_migrations(version, …) shape.
BEGIN;
DELETE FROM routing_rules WHERE id IN ('r_to_cfo', 'r_to_cmo', 'r_to_architect', 'r_to_product', 'r_to_engineering', 'r_to_design', 'r_to_ui', 'r_to_qa', 'r_to_sales', 'r_to_support', 'r_to_web3', 'r_to_legal', 'r_to_coo', 'r_to_orch', 'r_to_governance', 'r_to_guard', 'r_fallback', 'r_mirror_coo', 'r_mirror_ceo', 'r_mirror_architect', 'r_mirror_cfo', 'r_mirror_eng');
DELETE FROM schema_migrations WHERE version = '002-routing-rules';
COMMIT;
