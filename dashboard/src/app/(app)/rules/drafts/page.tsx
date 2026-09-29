import Link from "next/link";

import { Card, PageHeader } from "@/components/ui";
import { officialApi } from "@/lib/api";
import type { RuleDraft } from "@/lib/types";

import { DraftDecision } from "./decision";

export const metadata = { title: "Rule drafts" };

function value(draft: RuleDraft, amount: number): string {
  if (draft.unit === "currency-INR") return `₹${amount.toLocaleString("en-IN")}`;
  if (draft.unit === "percent") return `${amount}%`;
  if (draft.unit === "year") return `${amount} years`;
  return String(amount);
}

// Parameters split by course share a description; the course comes from the parameter's path.
const COURSES: Record<string, string> = { masters: "Master's course", phd: "Ph.D", postdoc: "Post-doctoral research" };

function title(draft: RuleDraft): string {
  const course = COURSES[draft.parameter.split(".").at(-1) ?? ""];
  return course ? `${draft.description} · ${course}` : draft.description;
}

function figurePattern(draft: RuleDraft): RegExp {
  const n = draft.found_value;
  const number = String(n).replace(".", "\\.");
  if (draft.unit === "year") return new RegExp(`\\b${number}\\s*years`, "gi");
  if (draft.unit === "percent") return new RegExp(`\\b${number}\\s*(?:%|per\\s?cent)`, "gi");
  const lakh = String(n / 100000).replace(".", "\\.");
  const indian = n.toLocaleString("en-IN").replaceAll(",", ",?");
  return new RegExp(`(?:${lakh}\\s*lakh|${indian})`, "gi");
}

/** The excerpt with the figure the draft is about marked, so the reviewer finds it at once. */
function Excerpt({ draft }: { draft: RuleDraft }) {
  const pattern = figurePattern(draft);
  const parts: React.ReactNode[] = [];
  let last = 0;
  for (const match of draft.excerpt.matchAll(pattern)) {
    parts.push(draft.excerpt.slice(last, match.index));
    parts.push(
      <mark key={match.index} className="rounded bg-turmeric/40 px-0.5 font-semibold text-ink">
        {match[0]}
      </mark>,
    );
    last = (match.index ?? 0) + match[0].length;
  }
  parts.push(draft.excerpt.slice(last));
  return <>{parts}</>;
}

const STATUS = {
  proposed: "bg-turmeric-mist text-ink",
  matches: "bg-leaf-mist text-leaf",
  approved: "bg-peacock-mist text-peacock-deep",
  rejected: "bg-paper text-ink-soft",
} as const;

const STATUS_LABEL = {
  proposed: "Change to decide",
  matches: "Matches the rules",
  approved: "Approved",
  rejected: "Rejected",
};

export default async function DraftsPage() {
  const drafts = await officialApi<RuleDraft[]>("/ministry/rule-drafts");
  const nextSession = `${new Date().getFullYear() + 1}-07-01`;
  return (
    <>
      <Link href="/rules" className="text-sm font-semibold text-peacock-deep hover:underline">
        ← Scheme rules
      </Link>
      <PageHeader
        title="Rule drafts"
        subtitle="Figures read from new guidelines, set against the rules in force. An approved change becomes a new parameter file for the rules repository, tested before it takes effect."
      />
      {drafts.length === 0 ? (
        <p className="rounded-2xl border-[1.5px] border-dashed border-line bg-card p-10 text-center text-ink-soft">
          No guidelines checked yet.
        </p>
      ) : (
        <ul className="space-y-3">
          {drafts.map((draft) => (
            <li key={draft.id}>
              <Card>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-xs font-semibold tracking-wide text-ink-soft uppercase">
                    {draft.scheme} · {draft.source_title}, page {draft.page}
                  </p>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS[draft.status]}`}>
                    {STATUS_LABEL[draft.status]}
                  </span>
                </div>
                <h2 className="mt-1 font-display text-lg font-bold">{title(draft)}</h2>
                <p className="mt-2 text-lg tabular">
                  {draft.status === "matches" ? (
                    <>
                      Still <span className="font-semibold">{value(draft, draft.current_value)}</span>
                    </>
                  ) : (
                    <>
                      <span className="text-ink-soft line-through">{value(draft, draft.current_value)}</span> →{" "}
                      <span className="font-semibold">{value(draft, draft.found_value)}</span>
                    </>
                  )}
                </p>
                <blockquote className="mt-3 rounded-lg border-l-4 border-turmeric bg-paper p-3 text-sm [overflow-wrap:anywhere]">
                  <Excerpt draft={draft} />
                </blockquote>
                {draft.status === "proposed" && <DraftDecision id={draft.id} defaultDate={nextSession} />}
                {draft.status === "approved" && (
                  <p className="mt-3 text-sm">
                    Applies from {draft.effective_from}.{" "}
                    <a href={`/rules/drafts/${draft.id}/file`} className="font-semibold text-peacock-deep hover:underline">
                      Download the new parameter file
                    </a>
                  </p>
                )}
                {draft.note && <p className="mt-2 text-sm text-ink-soft">Note: {draft.note}</p>}
              </Card>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
