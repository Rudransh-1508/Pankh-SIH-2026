import type { ReactNode } from "react";

export function PageHeader({ title, subtitle, action }: { title: string; subtitle?: ReactNode; action?: ReactNode }) {
  return (
    <header className="mb-8 flex flex-wrap items-end justify-between gap-4">
      <div className="space-y-1">
        <h1 className="font-display text-3xl font-bold">{title}</h1>
        {subtitle && <p className="text-ink-soft">{subtitle}</p>}
      </div>
      {action}
    </header>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-2xl border-[1.5px] border-line bg-card p-5 ${className}`}>{children}</section>;
}

export function Stat({ label, value, tone = "ink" }: { label: string; value: ReactNode; tone?: "ink" | "leaf" | "turmeric" | "laterite" | "peacock" }) {
  const tones = {
    ink: "text-ink",
    leaf: "text-leaf",
    turmeric: "text-[#9a6e00]",
    laterite: "text-laterite",
    peacock: "text-peacock-deep",
  };
  return (
    <div className="space-y-1">
      <p className="text-xs font-semibold tracking-wide text-ink-soft uppercase">{label}</p>
      <p className={`font-display text-3xl font-bold tabular ${tones[tone]}`}>{value}</p>
    </div>
  );
}

const KIND_LABELS: Record<string, string> = {
  name_mismatch: "Name differs",
  dob_mismatch: "Date of birth differs",
  stale_document: "Old certificate",
  value_conflict: "Answer differs",
  unreadable_document: "Unreadable document",
};

export function KindBadge({ kind }: { kind: string }) {
  return (
    <span className="inline-flex rounded-full bg-turmeric-mist px-2.5 py-0.5 text-xs font-semibold text-ink">
      {KIND_LABELS[kind] ?? kind}
    </span>
  );
}

/** How closely two names match, as a bar and a number, never colour alone. */
export function ScoreMeter({ score }: { score: number | null }) {
  if (score === null) return <span className="text-ink-soft">·</span>;
  const tone = score >= 0.9 ? "bg-leaf" : score >= 0.75 ? "bg-turmeric" : "bg-laterite";
  return (
    <span className="inline-flex items-center gap-2" title={`Name match ${Math.round(score * 100)}%`}>
      <span className="h-1.5 w-16 overflow-hidden rounded-full bg-line">
        <span className={`block h-full ${tone}`} style={{ width: `${Math.round(score * 100)}%` }} />
      </span>
      <span className="text-sm tabular">{Math.round(score * 100)}%</span>
    </span>
  );
}

export function percent(share: number): string {
  return `${Math.round(share * 1000) / 10}%`;
}

export function number(value: number): string {
  return value.toLocaleString("en-IN");
}

export const FACT_LABELS: Record<string, string> = {
  is_scheduled_tribe: "Scheduled Tribe",
  family_income: "Family income",
  date_of_birth: "Date of birth",
  education_level: "Course",
  net_jrf_qualified: "NET qualified",
  institution_recognised: "Recognised institution",
  institution_eligible_for_fellowship: "Fellowship-eligible university",
  has_aadhaar_seeded_bank_account: "Aadhaar-linked bank account",
};
