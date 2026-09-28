import Link from "next/link";

import { Card, FACT_LABELS, KindBadge, ScoreMeter } from "@/components/ui";
import { officialApi } from "@/lib/api";
import type { Case } from "@/lib/types";

import { DecisionForm } from "./decision-form";

export const metadata = { title: "Case" };

const SOURCES: Record<string, string> = {
  digilocker: "DigiLocker",
  self_declared: "student's answer",
  reviewer: "reviewer",
  aishe: "AISHE",
  udise: "UDISE+",
  nta: "NTA",
  npci: "NPCI",
};

function display(value: unknown): string {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return new Date(`${value}T00:00:00`).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" });
  }
  if (typeof value === "number") return value.toLocaleString("en-IN");
  return String(value);
}

export default async function CasePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const item = await officialApi<Case>(`/review/exceptions/${id}`);
  const comparison = item.name_comparison;
  return (
    <>
      <Link href="/review" className="text-sm font-semibold text-peacock-deep hover:underline">
        ← Review queue
      </Link>
      <header className="mt-3 mb-6 space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-display text-3xl font-bold">{item.student_name ?? "Unknown student"}</h1>
          <KindBadge kind={item.kind} />
        </div>
        <p className="text-ink-soft">
          {[item.district, item.state].filter(Boolean).join(", ")} · {FACT_LABELS[item.fact_name ?? ""] ?? item.fact_name} ·
          {item.days_open === 0 ? "waiting since today" : `waiting ${item.days_open} ${item.days_open === 1 ? "day" : "days"}`}
        </p>
      </header>
      <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
        <div className="space-y-5">
          <Card>
            <h2 className="mb-2 font-display text-xl font-bold">What we found</h2>
            <p className="text-lg">{item.message}</p>
            {item.remedy && <p className="mt-3 rounded-lg bg-paper p-3 text-sm text-ink-soft">Told the student: {item.remedy}</p>}
          </Card>
          {comparison && (
            <Card>
              <h2 className="mb-4 font-display text-xl font-bold">Names side by side</h2>
              <dl className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-xl bg-paper p-4">
                  <dt className="text-xs font-semibold tracking-wide text-ink-soft uppercase">On the certificate</dt>
                  <dd className="mt-1 text-xl font-semibold">{comparison.on_document}</dd>
                  <dd className="mt-1 font-mono text-xs text-ink-soft">sounds like: {comparison.keys[0]}</dd>
                </div>
                <div className="rounded-xl bg-paper p-4">
                  <dt className="text-xs font-semibold tracking-wide text-ink-soft uppercase">On Aadhaar</dt>
                  <dd className="mt-1 text-xl font-semibold">{comparison.on_aadhaar}</dd>
                  <dd className="mt-1 font-mono text-xs text-ink-soft">sounds like: {comparison.keys[1]}</dd>
                </div>
              </dl>
              <p className="mt-4 flex items-center gap-3 text-sm text-ink-soft">
                Match <ScoreMeter score={comparison.score} /> · automatic confirmation needs 90%
              </p>
            </Card>
          )}
          <Card>
            <h2 className="mb-3 font-display text-xl font-bold">Student&apos;s details</h2>
            <table className="w-full text-sm">
              <tbody>
                {Object.entries(item.facts).map(([name, fact]) => (
                  <tr key={name} className="border-b border-line last:border-0">
                    <td className="py-2 pr-4 text-ink-soft">{FACT_LABELS[name] ?? name.replaceAll("_", " ")}</td>
                    <td className="py-2 pr-4 font-semibold tabular">{display(fact.value)}</td>
                    <td className="py-2 text-right text-xs">
                      {fact.verified ? (
                        <span className="font-semibold text-leaf">✓ Confirmed · {SOURCES[fact.source] ?? fact.source}</span>
                      ) : (
                        <span className="text-ink-soft">Not confirmed · {SOURCES[fact.source] ?? fact.source}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {item.documents.length > 0 && (
              <p className="mt-4 text-sm text-ink-soft">DigiLocker documents: {item.documents.join(", ")}</p>
            )}
          </Card>
        </div>
        <Card className="h-fit lg:sticky lg:top-8">
          {item.status === "open" ? (
            <DecisionForm id={item.id} canConfirm={item.fact_name !== null} />
          ) : (
            <div className="space-y-2">
              <h2 className="font-display text-xl font-bold">{item.status === "resolved" ? "Confirmed" : "Returned to student"}</h2>
              <p className="text-ink-soft">{item.resolution}</p>
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
