// Shared domain types mirroring backend response shapes.

export interface Insight {
  id: string;
  tenant_id?: string;
  resource_id: string;
  resource_type: string;
  severity: string; // high | medium | low
  category: string; // cost_optimization | performance | availability | security | reliability
  issue: string;
  recommendation: string;
  confidence: string; // high | medium | low
  estimated_monthly_waste: number;
  avg_cpu: number | null;
  instance_type: string | null;
  window_days: number | null;
  observed_cost?: number | null;
  inactive_hours?: number | null;
  aws_account_id?: string | null;
  region?: string | null;
  status?: string;
  evidence?: string | null;
  created_at?: string;
}

export interface AnalyzeResponse {
  tenant_id: string;
  insights_found: number;
  insights: Insight[];
}

export interface ExplainResponse {
  answer: string;
  model: string;
  insight_id: string;
}

// Normalized inventory rows (parsed from raw boto3 responses).
export interface Ec2Row {
  resourceId: string;
  name: string;
  type: string;
  region: string;
  status: string;
  tags: Record<string, string>;
  lastSeen: string;
}

export interface RdsRow {
  resourceId: string;
  name: string;
  engine: string;
  region: string;
  status: string;
  instanceClass: string;
  lastSeen: string;
}

export interface LambdaRow {
  resourceId: string;
  name: string;
  runtime: string;
  region: string;
  memoryMb: number;
  lastSeen: string;
}
