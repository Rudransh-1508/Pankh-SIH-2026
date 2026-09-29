import Link from "next/link";

import { Card, Stat } from "@/components/ui";
import { officialApi } from "@/lib/api";
import type { Campaign } from "@/lib/types";

import { decideCampaign } from "../actions";
import { channelLabel, formatDate, StatusBadge, where } from "../campaign-summary";

export const metadata = { title: "Campaign" };

function NotYet() {
  return <span className="font-sans text-base font-semibold text-ink-soft">Not yet</span>;
}

export default async function CampaignPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const campaign = await officialApi<Campaign>(`/outreach/campaigns/${id}`);
  const recipients = campaign.channel === "school" ? campaign.schools : campaign.students;
  const noun = campaign.channel === "school" ? (recipients === 1 ? "school" : "schools") : recipients === 1 ? "family" : "families";
  const delivered = campaign.delivery.sent ?? 0;
  const missed = (campaign.delivery.no_contact ?? 0) + (campaign.delivery.failed ?? 0);
  return (
    <>
      <Link href="/outreach" className="text-sm font-semibold text-peacock-deep hover:underline">
        ← Outreach
      </Link>
      <header className="mt-3 mb-6 space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-display text-3xl font-bold">{where(campaign)}</h1>
          <StatusBadge status={campaign.status} />
        </div>
        <p className="text-ink-soft">
          {channelLabel(campaign)} · {campaign.sent_at ? `sent ${formatDate(campaign.sent_at)}` : `drafted ${formatDate(campaign.created_at)}`}
        </p>
      </header>

      <div className="mb-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <Stat label="Students" value={campaign.students.toLocaleString("en-IN")} />
        </Card>
        <Card>
          <Stat label="Schools" value={campaign.schools.toLocaleString("en-IN")} />
        </Card>
        <Card>
          <Stat label="Students told" value={campaign.status === "sent" ? delivered.toLocaleString("en-IN") : <NotYet />} tone="peacock" />
        </Card>
        <Card>
          <Stat
            label="Applied since"
            value={campaign.applied_since === null ? <NotYet /> : campaign.applied_since.toLocaleString("en-IN")}
            tone="leaf"
          />
        </Card>
      </div>

      {campaign.status === "draft" && (
        <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
          <Card>
            <h2 className="mb-1 font-display text-xl font-bold">What will be sent</h2>
            <p className="mb-4 text-sm text-ink-soft">
              {campaign.preview.length < recipients ? `The first ${campaign.preview.length} of ${recipients} messages.` : "Every message."} Contacts
              come from UDISE+ when sending and are not stored.
            </p>
            <ul className="space-y-3">
              {campaign.preview.map((message, index) => (
                <li key={index} className="rounded-xl bg-paper p-4">
                  <p className="text-xs font-semibold tracking-wide text-ink-soft uppercase">
                    {message.to === "school" ? `To the nodal officer, ${message.school} · ${message.students} students` : "To the family"}
                  </p>
                  <p className="mt-2 [overflow-wrap:anywhere]">{message.text}</p>
                </li>
              ))}
            </ul>
            {campaign.skipped_recent > 0 && (
              <p className="mt-4 text-sm text-ink-soft">
                {campaign.skipped_recent} students were left out because they were messaged this way in the last 30 days.
              </p>
            )}
          </Card>
          <Card className="h-fit space-y-3 lg:sticky lg:top-8">
            <h2 className="font-display text-xl font-bold">Approve</h2>
            <p className="text-sm text-ink-soft">
              Sending is recorded in your name. Each message says applying is free
              {campaign.channel === "family" ? " and warns families that nobody will ask for money or an OTP" : ""}.
            </p>
            <form action={decideCampaign.bind(null, campaign.id, "send")}>
              <button className="w-full rounded-xl bg-peacock px-4 py-3 font-semibold text-white hover:bg-peacock-deep">
                Send to {recipients.toLocaleString("en-IN")} {noun}
              </button>
            </form>
            <form action={decideCampaign.bind(null, campaign.id, "cancel")}>
              <button className="w-full rounded-xl border-[1.5px] border-line px-4 py-3 font-semibold hover:border-peacock">
                Cancel the draft
              </button>
            </form>
          </Card>
        </div>
      )}

      {campaign.status === "sent" && (
        <Card>
          <h2 className="mb-2 font-display text-xl font-bold">Results</h2>
          <p>
            {delivered.toLocaleString("en-IN")} of {campaign.students.toLocaleString("en-IN")} students were told
            {missed > 0 ? `; ${missed} could not be reached because their school or family has no number in UDISE+` : ""}.
          </p>
          <p className="mt-2 text-ink-soft">
            {campaign.applied_since === null
              ? "Who has applied since shows after the next coverage run."
              : `${campaign.applied_since} have registered for a scholarship since, as of the latest coverage run.`}
          </p>
        </Card>
      )}
    </>
  );
}
