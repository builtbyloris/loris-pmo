export type HealthStatus = "HEALTHY" | "WATCH" | "AT_RISK" | "CRITICAL";
export type AlertSeverity = "INFO" | "WARNING" | "CRITICAL";
export type AlertStatus = "ACTIVE" | "ACKNOWLEDGED" | "RESOLVED";

export interface KPIValue {
  key: string;
  value: number | string | null;
  unit: string | null;
  status: string;
  available: boolean;
  reason: string | null;
}

export interface HealthDimension {
  key: string;
  score: number | null;
  status: HealthStatus | null;
  available: boolean;
  reason: string | null;
  weight: number;
  effective_weight: number;
  evidence: Record<string, unknown>;
}

export interface HealthDriver {
  key: string;
  severity: AlertSeverity;
  evidence: Record<string, unknown>;
}

export interface HealthHistoryItem {
  id: string;
  score: number;
  status: HealthStatus;
  trigger: string;
  created_at: string;
}

export interface HealthRead {
  score: number | null;
  status: HealthStatus | null;
  dimensions: HealthDimension[];
  drivers: HealthDriver[];
  calculated_at: string;
  history: HealthHistoryItem[];
}

export interface AlertRead {
  id: string;
  project_id: string;
  rule_type: string;
  severity: AlertSeverity;
  title_key: string;
  reason_key: string;
  evidence: Record<string, string | number | null>;
  related_entity_type: string | null;
  related_entity_id: string | null;
  status: AlertStatus;
  first_detected_at: string;
  last_detected_at: string;
  acknowledged_at: string | null;
  read_at: string | null;
  resolved_at: string | null;
}

export interface AutomationRule {
  key: string;
  trigger: string;
  conditions: string[];
  actions: string[];
  enabled: boolean;
}

export interface ProjectIntelligence {
  project_id: string;
  kpis: KPIValue[];
  health: HealthRead;
  alerts: AlertRead[];
  automation_rules: AutomationRule[];
}

export interface PortfolioProjectIntelligence {
  project_id: string;
  project_name: string;
  project_code: string;
  health_score: number | null;
  health_status: HealthStatus | null;
  overdue_tasks: number;
  high_critical_risks: number;
  critical_issues: number;
  budget_status: string;
  active_alerts: number;
}

export interface PortfolioIntelligence {
  healthy_projects: number;
  watch_projects: number;
  at_risk_projects: number;
  critical_projects: number;
  active_critical_alerts: number;
  total_overdue_tasks: number;
  total_high_critical_risks: number;
  projects: PortfolioProjectIntelligence[];
}
