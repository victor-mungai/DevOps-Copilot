-- Remove legacy synthetic/demo findings that predate AWS-source-of-truth rules.
-- These identifiers were never guaranteed to exist in the connected tenant's AWS account.

DELETE FROM insights
WHERE resource_id IN (
    'db-prod-pg',
    'process-telemetry',
    'vol-0912',
    'snap-0987654321fedcba0',
    'vol-0123456789abcdef0',
    'i-060a947e1e823ea71',
    'i-0ad3c6e402779dc42'
);
