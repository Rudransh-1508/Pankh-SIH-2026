import { Card, number, PageHeader } from "@/components/ui";
import { officialApi } from "@/lib/api";
import type { Pipeline } from "@/lib/types";

export const metadata = { title: "Pipeline" };

// The order NSP moves applications through, with defects set apart.
const STATUS_ORDER = [
  "Submitted",
  "Verified by Institute",
  "Verified by District",
  "Verified by State",
  "Sanctioned",
  "Payment Initiated",
  "Paid",
];

const COLORS: Record<string, string> = {
  Submitted: "#c9d3e3",
  "Verified by Institute": "#9fb8c9",
  "Verified by District": "#6f9fb0",
  "Verified by State": "#3f8791",
  Sanctioned: "#0e6f78",
  "Payment Initiated": "#5d9a6f",
  Paid: "#2f7d4f",
};

function color(status: string): string {
  return COLORS[status] ?? (status.startsWith("Defective") ? "#e9a800" : "#b3412e");
}

export default async function PipelinePage() {
  const pipeline = await officialApi<Pipeline>("/ministry/pipeline");
  const statuses = [
    ...STATUS_ORDER,
    ...new Set(pipeline.states.flatMap((s) => Object.keys(s.statuses)).filter((s) => !STATUS_ORDER.includes(s))),
  ];
  return (
    <>
      <PageHeader title="Pipeline" subtitle="Where NSP applications sit now. Long bars before “Sanctioned” mean verification is slow." />
      <Card className="mb-6">
        <ul className="flex flex-wrap gap-x-4 gap-y-2 text-xs text-ink-soft">
          {statuses.map((status) => (
            <li key={status} className="flex items-center gap-1.5">
              <span className="inline-block size-2.5 rounded-sm" style={{ background: color(status) }} />
              {status}
            </li>
          ))}
        </ul>
      </Card>
      <div className="space-y-4">
        {pipeline.states.map((state) => (
          <Card key={state.state}>
            <div className="mb-3 flex items-baseline justify-between">
              <h2 className="font-semibold">{state.state}</h2>
              <p className="text-sm text-ink-soft tabular">{number(state.total)} applications</p>
            </div>
            <div className="flex h-7 w-full overflow-hidden rounded-lg">
              {statuses
                .filter((status) => state.statuses[status])
                .map((status) => (
                  <span
                    key={status}
                    title={`${status}: ${state.statuses[status]}`}
                    style={{ width: `${(state.statuses[status] / state.total) * 100}%`, background: color(status) }}
                  />
                ))}
            </div>
            <p className="mt-2 text-xs text-ink-soft tabular">
              {number(Object.entries(state.statuses).filter(([s]) => s.startsWith("Defective")).reduce((a, [, n]) => a + n, 0))} marked
              defective ·{" "}
              {number(state.statuses["Paid"] ?? 0)} paid
            </p>
          </Card>
        ))}
      </div>
    </>
  );
}
