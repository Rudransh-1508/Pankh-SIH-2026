import Link from "next/link";

import { PageHeader } from "@/components/ui";
import { officialApi } from "@/lib/api";
import type { Official, Reminder } from "@/lib/types";

import { decideReminder, sweep } from "./actions";

export const metadata = { title: "Reminders" };

const TABS = [
  { status: "proposed", label: "To approve" },
  { status: "sent", label: "Sent" },
  { status: "dismissed", label: "Dismissed" },
] as const;

export default async function RemindersPage({ searchParams }: { searchParams: Promise<{ status?: string }> }) {
  const { status = "proposed" } = await searchParams;
  const [official, reminders] = await Promise.all([
    officialApi<Official>("/review/me"),
    officialApi<Reminder[]>(`/review/nudges?status=${encodeURIComponent(status)}`),
  ]);
  return (
    <>
      <PageHeader
        title="Reminders"
        subtitle="Applications waiting longer than the guideline timelines. Nothing is sent to an office until you approve it."
        action={
          official.level === "ministry" ? (
            <form action={sweep}>
              <button className="rounded-xl border-[1.5px] border-line bg-card px-4 py-2.5 text-sm font-semibold hover:border-peacock">
                Check all students now
              </button>
            </form>
          ) : undefined
        }
      />
      <div className="mb-5 flex flex-wrap gap-2" role="tablist">
        {TABS.map((tab) => (
          <Link
            key={tab.status}
            href={`/reminders?status=${tab.status}`}
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
      {reminders.length === 0 ? (
        <p className="rounded-2xl border-[1.5px] border-dashed border-line bg-card p-10 text-center text-ink-soft">
          {status === "proposed" ? "No stalled applications in your area right now." : "Nothing here yet."}
        </p>
      ) : (
        <ul className="space-y-3">
          {reminders.map((reminder) => (
            <li key={reminder.id} className="rounded-2xl border-[1.5px] border-line bg-card p-5">
              <p className="text-xs font-semibold tracking-wide text-ink-soft uppercase">
                {reminder.kind === "callback_request" ? "Callback requested" : `To the ${reminder.level} office`} ·{" "}
                {[reminder.district, reminder.state].filter(Boolean).join(", ")}
              </p>
              <p className="mt-2 text-lg">{reminder.message}</p>
              {reminder.status === "proposed" && (
                <div className="mt-4 flex flex-wrap gap-2">
                  <form action={decideReminder.bind(null, reminder.id, "approve")}>
                    <button className="rounded-xl bg-peacock px-4 py-2.5 text-sm font-semibold text-white hover:bg-peacock-deep">
                      {reminder.kind === "callback_request" ? "Mark as called back" : "Approve and send"}
                    </button>
                  </form>
                  <form action={decideReminder.bind(null, reminder.id, "dismiss")}>
                    <button className="rounded-xl border-[1.5px] border-line px-4 py-2.5 text-sm font-semibold hover:border-peacock">
                      Dismiss
                    </button>
                  </form>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
