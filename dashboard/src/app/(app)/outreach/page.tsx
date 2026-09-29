import Link from "next/link";

import { Card, PageHeader } from "@/components/ui";
import { ApiError, officialApi } from "@/lib/api";
import type { Campaign, Coverage, Official } from "@/lib/types";

import { channelLabel, formatDate, StatusBadge, where } from "./campaign-summary";
import { DraftForm, type Scope } from "./draft-form";

export const metadata = { title: "Outreach" };

async function scopeFor(official: Official): Promise<Scope | null> {
  if (official.level === "district") return { states: [], fixed: `${official.district}, ${official.state}` };
  try {
    const coverage = await officialApi<Coverage>("/ministry/coverage");
    return {
      fixed: null,
      states: coverage.states
        .filter((s) => s.unreached > 0)
        .map((s) => ({ state: s.state, districts: s.districts.filter((d) => d.unreached > 0).map((d) => d.district) })),
    };
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export default async function OutreachPage() {
  const official = await officialApi<Official>("/review/me");
  const [scope, campaigns] = await Promise.all([scopeFor(official), officialApi<Campaign[]>("/outreach/campaigns")]);
  return (
    <>
      <PageHeader
        title="Outreach"
        subtitle="Tell Unreached Students, through their schools or their families, which scholarships they may qualify for."
      />
      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-3">
          <h2 className="font-display text-xl font-bold">Campaigns</h2>
          {campaigns.length === 0 ? (
            <p className="rounded-2xl border-[1.5px] border-dashed border-line bg-card p-10 text-center text-ink-soft">
              No campaigns yet. Draft one to see its messages.
            </p>
          ) : (
            <ul className="space-y-3">
              {campaigns.map((campaign) => (
                <li key={campaign.id}>
                  <Link
                    href={`/outreach/${campaign.id}`}
                    className="block rounded-2xl border-[1.5px] border-line bg-card p-5 transition hover:border-peacock"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="font-display text-lg font-bold">{where(campaign)}</p>
                      <StatusBadge status={campaign.status} />
                    </div>
                    <p className="mt-1 text-sm text-ink-soft">
                      {channelLabel(campaign)} · {formatDate(campaign.sent_at ?? campaign.created_at)}
                    </p>
                    <p className="mt-3 text-sm tabular">
                      <span className="font-semibold">{campaign.students.toLocaleString("en-IN")}</span> students in{" "}
                      <span className="font-semibold">{campaign.schools.toLocaleString("en-IN")}</span> schools
                      {campaign.applied_since !== null && (
                        <>
                          {" "}
                          · <span className="font-semibold text-leaf">{campaign.applied_since} applied since</span>
                        </>
                      )}
                    </p>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
        <Card className="h-fit lg:sticky lg:top-8">
          <h2 className="mb-4 font-display text-xl font-bold">New campaign</h2>
          {scope === null ? (
            <p className="text-ink-soft">There is no coverage run yet, so there is no one to contact. The ministry starts one from Coverage.</p>
          ) : scope.fixed === null && scope.states.length === 0 ? (
            <p className="text-ink-soft">Every enrolled student in your area has applied. There is no one to contact.</p>
          ) : (
            <DraftForm scope={scope} />
          )}
        </Card>
      </div>
    </>
  );
}
