import Link from "next/link";

import { KindBadge, PageHeader, ScoreMeter, FACT_LABELS } from "@/components/ui";
import { officialApi } from "@/lib/api";
import type { QueueItem } from "@/lib/types";

export const metadata = { title: "Review queue" };

const TABS = [
  { status: "open", label: "Waiting" },
  { status: "rejected", label: "Returned to student" },
  { status: "resolved", label: "Confirmed" },
] as const;

export default async function ReviewPage({ searchParams }: { searchParams: Promise<{ status?: string }> }) {
  const { status = "open" } = await searchParams;
  const items = await officialApi<QueueItem[]>(`/review/exceptions?status=${encodeURIComponent(status)}`);
  return (
    <>
      <PageHeader
        title="Review queue"
        subtitle="Details that could not be confirmed automatically. Students who have waited longest are first."
      />
      <div className="mb-5 flex flex-wrap gap-2" role="tablist">
        {TABS.map((tab) => (
          <Link
            key={tab.status}
            href={`/review?status=${tab.status}`}
            role="tab"
            aria-selected={tab.status === status}
            className={`rounded-full border-[1.5px] px-4 py-1.5 text-sm font-semibold ${
              tab.status === status ? "border-peacock bg-peacock-mist text-peacock-deep" : "border-line bg-card text-ink-soft"
            }`}
          >
            {tab.label}
          </Link>
        ))}
      </div>
      {items.length === 0 ? (
        <p className="rounded-2xl border-[1.5px] border-dashed border-line bg-card p-10 text-center text-ink-soft">
          {status === "open" ? "Nothing is waiting for you. New cases appear here as students link DigiLocker." : "No cases here yet."}
        </p>
      ) : (
        <div className="overflow-hidden rounded-2xl border-[1.5px] border-line bg-card">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-line bg-paper text-xs tracking-wide text-ink-soft uppercase">
              <tr>
                <th className="px-4 py-3 font-semibold">Student</th>
                <th className="hidden px-4 py-3 font-semibold md:table-cell">Detail</th>
                <th className="px-4 py-3 font-semibold">Issue</th>
                <th className="hidden px-4 py-3 font-semibold sm:table-cell">Name match</th>
                <th className="px-4 py-3 text-right font-semibold">Waiting</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-line last:border-0 hover:bg-paper">
                  <td className="px-4 py-3.5">
                    <Link href={`/review/${item.id}`} className="font-semibold text-ink hover:text-peacock-deep hover:underline">
                      {item.student_name ?? "Unknown student"}
                    </Link>
                    <p className="text-xs text-ink-soft">{[item.district, item.state].filter(Boolean).join(", ")}</p>
                  </td>
                  <td className="hidden px-4 py-3.5 md:table-cell">{FACT_LABELS[item.fact_name ?? ""] ?? item.fact_name ?? "·"}</td>
                  <td className="px-4 py-3.5">
                    <KindBadge kind={item.kind} />
                  </td>
                  <td className="hidden px-4 py-3.5 sm:table-cell">
                    <ScoreMeter score={item.kind === "name_mismatch" ? item.match_score : null} />
                  </td>
                  <td className={`px-4 py-3.5 text-right tabular ${item.days_open > 7 ? "font-semibold text-laterite" : ""}`}>
                    {item.days_open === 0 ? "Today" : `${item.days_open} d`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
