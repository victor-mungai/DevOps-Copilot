-- Cost Explorer permits at most two GroupBy dimensions. SERVICE + REGION is
-- retained as authoritative attribution; dimensions not returned by AWS stay NULL.
ALTER TABLE aws_costs ALTER COLUMN usage_type DROP NOT NULL;
ALTER TABLE aws_costs ALTER COLUMN record_type DROP NOT NULL;
ALTER TABLE aws_costs ALTER COLUMN region DROP NOT NULL;
