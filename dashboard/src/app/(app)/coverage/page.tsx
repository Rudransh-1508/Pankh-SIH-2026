import Link from "next/link";

import { Card, number, PageHeader, percent, Stat } from "@/components/ui";
import { ApiError, officialApi } from "@/lib/api";
import type { Coverage, Official } from "@/lib/types";

import { RunButton } from "./run-button";

export const metadata = { title: "Coverage" };

function CoverageBar({ reached, possible, enrolled }: { reached: number; possible: number; enrolled: number }) {
  const share = (value: number) => `${enrolled ? (value / enrolled) * 100 : 0}%`;
  return (
    <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-laterite-mist" aria-hidden>
      <span className="bg-leaf" style={{ width: share(reached) }} />
      <span className="bg-turmeric" style={{ width: share(possible) }} />
    </div>
  );
}

export default async function CoveragePage() {
  const official = await officialApi<Official>("/review/me");
  let coverage: Coverage | null = null;
  try {
    coverage = await officialApi<Coverage>("/ministry/coverage");
  } catch (error) {
    if (!(error instanceof ApiError && error.status === 404)) throw error;
  }
  const canRun = official.level === "ministry";
  if (!coverage) {
    return (
      <>
        <PageHeader title="Coverage" subtitle="Enrolled ST students who are not yet getting a scholarship." />
        <Card className="space-y-4 text-center">
          <p className="text-ink-soft">No linkage has been run yet.</p>
          {canRun && (
            <div className="flex justify-center">
              <RunButton />
            </div>
          )}
        </Card>
      </>
    );
  }
  const { totals } = coverage;
  const ran = new Date(coverage.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
  return (
    <>
      <PageHeader
        title="Coverage"
        subtitle={`ST students on the UDISE+ roster, linked against ${number(coverage.registrations)} NSP registrations · ${ran}`}
        action={canRun ? <RunButton label="Run again" /> : undefined}
      />
      <Card className="mb-6">
        <div className="grid grid-cols-2 gap-6 lg:grid-cols-5">
          <Stat label="Enrolled ST" value={number(totals.enrolled)} />
          <Stat label="Registered" value={number(totals.reached)} tone="leaf" />
          <Stat label="To confirm" value={number(totals.possible)} tone="turmeric" />
          <Stat label="Not reached" value={number(totals.unreached)} tone="laterite" />
          <Stat label="Coverage" value={percent(totals.coverage)} tone="peacock" />
        </div>
        <div className="mt-6">
          <CoverageBar {...totals} />
          <p className="mt-2 flex flex-wrap gap-4 text-xs text-ink-soft">
            <span><span className="mr-1 inline-block size-2 rounded-full bg-leaf" />Registered</span>
            <span><span className="mr-1 inline-block size-2 rounded-full bg-turmeric" />Possible match</span>
            <span><span className="mr-1 inline-block size-2 rounded-full bg-laterite-mist ring-1 ring-laterite" />Not reached</span>
          </p>
        </div>
      </Card>

      <div className="space-y-3">
        {coverage.states
          .toSorted((a, b) => a.coverage - b.coverage)
          .map((state) => (
            <details key={state.state} className="group rounded-2xl border-[1.5px] border-line bg-card">
              <summary className="grid cursor-pointer list-none grid-cols-[1fr_auto_auto] items-center gap-4 p-5 sm:grid-cols-[180px_1fr_auto_auto]">
                <span className="font-semibold">{state.state}</span>
                <span className="hidden sm:block">
                  <CoverageBar {...state} />
                </span>
                <span className="text-right text-sm tabular">
                  <span className="font-semibold text-laterite">{number(state.unreached)}</span> not reached
                </span>
                <span className="w-16 text-right font-display text-xl font-bold tabular text-peacock-deep">
                  {percent(state.coverage)}
                </span>
              </summary>
              <div className="border-t border-line px-5 pb-5">
                {state.official && (
                  <p className="mt-4 rounded-lg bg-paper p-3 text-sm text-ink-soft">
                    Official beneficiaries, FY {state.official.financial_year}:{" "}
                    <span className="font-semibold text-ink tabular">{number(state.official.total)}</span>
                    {state.official.pre_matric !== undefined && ` (Pre-Matric ${number(state.official.pre_matric)}`}
                    {state.official.post_matric !== undefined && `, Post-Matric ${number(state.official.post_matric)})`}
                  </p>
                )}
                <table className="mt-4 w-full text-sm">
                  <thead className="text-xs tracking-wide text-ink-soft uppercase">
                    <tr>
                      <th className="py-2 text-left font-semibold">District</th>
                      <th className="py-2 text-right font-semibold">Enrolled</th>
                      <th className="py-2 text-right font-semibold">Registered</th>
                      <th className="py-2 text-right font-semibold">Not reached</th>
                      <th className="py-2 text-right font-semibold">Coverage</th>
                    </tr>
                  </thead>
                  <tbody className="tabular">
                    {state.districts.map((d) => (
                      <tr key={d.district} className="border-t border-line">
                        <td className="py-2">
                          <Link
                            className="font-semibold text-peacock-deep hover:underline"
                            href={`/coverage/unreached?state=${encodeURIComponent(state.state)}&district=${encodeURIComponent(d.district)}`}
                          >
                            {d.district}
                          </Link>
                        </td>
                        <td className="py-2 text-right">{number(d.enrolled)}</td>
                        <td className="py-2 text-right">{number(d.reached)}</td>
                        <td className="py-2 text-right font-semibold text-laterite">{number(d.unreached)}</td>
                        <td className="py-2 text-right">{percent(d.coverage)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          ))}
      </div>
      <p className="mt-8 max-w-3xl text-xs text-ink-soft">
        {coverage.method} Registers here are synthetic. Official figures: {coverage.official_source}.
      </p>
    </>
  );
}
