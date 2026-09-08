export interface UserPublic {
  id: string;
  email: string;
  display_name: string;
  role: string;
  subscription_tier: string;
  skill_level: string;
  xp: number;
  current_streak_days: number;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserPublic;
}

export interface IncidentListItem {
  id: string;
  slug: string;
  title: string;
  difficulty: string;
  category: string;
  priority: string;
  summary: string;
  is_free_tier: boolean;
  xp_reward: number;
}

export interface TopologyNode {
  id: string;
  label: string;
  type: "pc" | "switch" | "router" | "server";
}

export interface TopologyEdge {
  from: string;
  to: string;
  from_if: string;
  to_if: string;
}

export interface IncidentPublic {
  id: string;
  slug: string;
  title: string;
  difficulty: string;
  category: string;
  priority: string;
  summary: string;
  impact: string;
  symptoms: string[];
  learning_objectives: string[];
  topology: { nodes: TopologyNode[]; edges: TopologyEdge[] };
  xp_reward: number;
}

export interface AttemptPublic {
  id: string;
  incident_id: string;
  status: "in_progress" | "resolved" | "abandoned";
  hints_used: number;
  failed_attempts: number;
  unnecessary_commands: number;
  root_cause_identified: boolean;
  remediation_applied: boolean;
  verification_passed: boolean;
  methodology_progress: Record<string, boolean>;
  score_diagnosis: number | null;
  score_methodology: number | null;
  score_efficiency: number | null;
  score_remediation: number | null;
  score_verification: number | null;
  score_overall: number | null;
}

export interface CoachTurn {
  role: "coach" | "student";
  text: string;
}

export interface ResolutionSummary {
  attempt: AttemptPublic;
  root_cause: string;
  correct_remediation: string;
  verification_procedure: string;
  explanation: string;
}

export interface DashboardSummary {
  display_name: string;
  skill_level: string;
  overall_skill_percent: number;
  troubleshooting_score_percent: number;
  incidents_completed: number;
  incidents_solved: number;
  average_resolution_seconds: number | null;
  hints_used_total: number;
  strongest_skill: string | null;
  weakest_skill: string | null;
  current_streak_days: number;
  xp: number;
  recommended_next: string;
}

export interface ReadinessReport {
  fundamentals: number;
  layer1: number;
  layer2_switching: number;
  layer3_routing: number;
  network_services: number;
  security: number;
  monitoring: number;
  troubleshooting_methodology: number;
  communication: number;
  overall_readiness: number;
  level: string;
  improvement_areas: string[];
}
