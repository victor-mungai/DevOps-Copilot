import { apiFetch } from './api';
import type { Ec2Row, LambdaRow, RdsRow } from './types';

// The aws-connector returns raw boto3 responses under a `data` key. These
// helpers fetch and normalize them into flat rows for tables/counts.

interface RawWrapper {
  data?: Record<string, unknown>;
}

function tagsToMap(tags: unknown): Record<string, string> {
  const out: Record<string, string> = {};
  if (Array.isArray(tags)) {
    for (const t of tags) {
      if (t && typeof t === 'object' && 'Key' in t && 'Value' in t) {
        out[String((t as any).Key).trim()] = String((t as any).Value);
      }
    }
  }
  return out;
}

function withRegion(path: string, region?: string): string {
  return region ? `${path}?region=${encodeURIComponent(region)}` : path;
}

export async function fetchEc2(tenantId: string, region?: string): Promise<Ec2Row[]> {
  const res = await apiFetch<RawWrapper>(withRegion(`/v1/aws/${tenantId}/ec2/instances`, region), {
    tenantId,
  });
  const reservations = (res.data?.Reservations as any[]) ?? [];
  const rows: Ec2Row[] = [];
  for (const reservation of reservations) {
    for (const inst of reservation?.Instances ?? []) {
      const id = inst?.InstanceId;
      if (!id) continue;
      const tags = tagsToMap(inst?.Tags);
      rows.push({
        resourceId: id,
        name: tags['Name'] ?? id,
        type: inst?.InstanceType ?? '—',
        region: inst?.Placement?.AvailabilityZone ?? '—',
        status: inst?.State?.Name ?? 'unknown',
        tags,
        lastSeen: inst?.LaunchTime ?? '',
      });
    }
  }
  return rows;
}

export async function fetchRds(tenantId: string, region?: string): Promise<RdsRow[]> {
  const res = await apiFetch<RawWrapper>(withRegion(`/v1/aws/${tenantId}/rds/databases`, region), {
    tenantId,
  });
  const dbs = (res.data?.DBInstances as any[]) ?? [];
  return dbs
    .filter((db) => db?.DBInstanceIdentifier)
    .map((db) => ({
      resourceId: db.DBInstanceIdentifier,
      name: db.DBInstanceIdentifier,
      engine: db?.Engine ?? '—',
      region: db?.AvailabilityZone ?? '—',
      status: db?.DBInstanceStatus ?? 'unknown',
      instanceClass: db?.DBInstanceClass ?? '—',
      lastSeen: db?.InstanceCreateTime ?? '',
    }));
}

export async function fetchLambda(tenantId: string, region?: string): Promise<LambdaRow[]> {
  const res = await apiFetch<RawWrapper>(
    withRegion(`/v1/aws/${tenantId}/lambda/functions`, region),
    { tenantId }
  );
  const fns = (res.data?.Functions as any[]) ?? [];
  return fns
    .filter((fn) => fn?.FunctionName)
    .map((fn) => ({
      resourceId: fn.FunctionName,
      name: fn.FunctionName,
      runtime: fn?.Runtime ?? '—',
      region: fn?.FunctionArn?.split(':')?.[3] ?? region ?? '—',
      memoryMb: Number(fn?.MemorySize ?? 0),
      lastSeen: fn?.LastModified ?? '',
    }));
}
