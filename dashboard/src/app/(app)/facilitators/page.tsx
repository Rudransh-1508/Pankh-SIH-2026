import { PageHeader } from "@/components/ui";
import { officialApi } from "@/lib/api";
import type { Facilitator } from "@/lib/types";

import { decideFacilitator } from "./actions";

export const metadata = { title: "Facilitators" };

export default async function FacilitatorsPage() {
  const pending = await officialApi<Facilitator[]>("/review/facilitators");
  return (
    <>
      <PageHeader
        title="Facilitators"
        subtitle="Teachers and field workers who asked to help students apply. Once approved, they can help a student only after the student shares a consent code sent to their own phone."
      />
      {pending.length === 0 ? (
        <p className="rounded-2xl border-[1.5px] border-dashed border-line bg-card p-10 text-center text-ink-soft">
          No one is waiting for approval in your area.
        </p>
      ) : (
        <ul className="space-y-3">
          {pending.map((f) => (
            <li key={f.id} className="rounded-2xl border-[1.5px] border-line bg-card p-5">
              <p className="font-display text-lg font-bold">{f.name}</p>
              <p className="text-ink-soft">
                {f.organisation} · {f.district}, {f.state}
                {f.phone ? ` · ${f.phone}` : ""}
              </p>
              <p className="mt-2 text-sm text-ink-soft">Check that they work where they say before approving.</p>
              <div className="mt-4 flex flex-wrap gap-2">
                <form action={decideFacilitator.bind(null, f.id, "approve")}>
                  <button className="rounded-xl bg-peacock px-4 py-2.5 text-sm font-semibold text-white hover:bg-peacock-deep">
                    Approve
                  </button>
                </form>
                <form action={decideFacilitator.bind(null, f.id, "reject")}>
                  <button className="rounded-xl border-[1.5px] border-line px-4 py-2.5 text-sm font-semibold hover:border-peacock">
                    Reject
                  </button>
                </form>
              </div>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
