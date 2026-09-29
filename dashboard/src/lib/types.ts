export type Level = "institute" | "district" | "state" | "ministry";

export interface Official {
  id: string;
  name: string;
  level: Level;
  state: string | null;
  district: string | null;
}

export interface QueueItem {
  id: string;
  student_name: string | null;
  district: string | null;
  state: string | null;
  fact_name: string | null;
  kind: string;
  message: string;
  match_score: number | null;
  level: Level;
  status: "open" | "resolved" | "rejected";
  days_open: number;
}

export interface Case extends QueueItem {
  remedy: string | null;
  evidence: Record<string, unknown>;
  resolution: string | null;
  facts: Record<string, { value: unknown; source: string; verified: boolean }>;
  documents: string[];
  name_comparison: { on_document: string; on_aadhaar: string; keys: [string, string]; score: number } | null;
}

export interface Counts {
  enrolled: number;
  reached: number;
  possible: number;
  unreached: number;
  coverage: number;
}

export interface StateCoverage extends Counts {
  state: string;
  districts: (Counts & { district: string })[];
  official: { financial_year: string; total: number; pre_matric?: number; post_matric?: number } | null;
}

export interface Coverage {
  id: string;
  created_at: string;
  totals: Counts;
  states: StateCoverage[];
  registrations: number;
  method: string;
  official_source: string;
}

export interface UnreachedStudent {
  student_ref: string;
  name: string;
  class: string;
  gender: string;
  district: string;
  state: string;
  udise_code: string;
  likely_schemes: { scheme_id: string; scheme: string; to_confirm: string[] }[];
}

export interface Pipeline {
  states: { state: string; total: number; statuses: Record<string, number> }[];
  waiting_on: Record<string, number>;
}

export interface Citation {
  source_title: string;
  page: number;
  clause: string;
  url: string;
}

export interface Rules {
  academic_year_label: string;
  schemes: {
    scheme: { id: string; name: string; short_name: string; summary: string; system_of_record: string };
    rules: { id: string; title: string; citation: Citation }[];
  }[];
}

export interface Reminder {
  id: string;
  kind: string;
  message: string;
  level: Level | null;
  district: string | null;
  state: string | null;
  status: "proposed" | "sent" | "dismissed";
  created_at: string;
}
