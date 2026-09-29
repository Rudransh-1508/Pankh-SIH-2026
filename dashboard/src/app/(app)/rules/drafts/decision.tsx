"use client";

import { useActionState } from "react";

import { decideDraft, type FormState } from "../actions";

export function DraftDecision({ id, defaultDate }: { id: string; defaultDate: string }) {
  const [state, action, pending] = useActionState<FormState, FormData>(decideDraft.bind(null, id), {});
  const field = "rounded-xl border-[1.5px] border-line bg-card p-2.5 outline-none focus:border-peacock";
  return (
    <form action={action} className="mt-4 flex flex-wrap items-end gap-3">
      <label className="space-y-1">
        <span className="block text-xs font-semibold text-ink-soft">Applies from</span>
        <input type="date" name="effective_from" defaultValue={defaultDate} className={field} />
      </label>
      <label className="min-w-48 flex-1 space-y-1">
        <span className="block text-xs font-semibold text-ink-soft">Note</span>
        <input name="note" placeholder="What you checked" className={`${field} w-full`} />
      </label>
      <button
        name="decision"
        value="approve"
        disabled={pending}
        className="rounded-xl bg-peacock px-4 py-2.5 text-sm font-semibold text-white hover:bg-peacock-deep disabled:opacity-60"
      >
        Approve
      </button>
      <button
        name="decision"
        value="reject"
        disabled={pending}
        className="rounded-xl border-[1.5px] border-line px-4 py-2.5 text-sm font-semibold hover:border-peacock disabled:opacity-60"
      >
        Reject
      </button>
      {state.error && (
        <p role="alert" className="w-full rounded-lg bg-laterite-mist px-3 py-2 text-sm text-laterite">
          {state.error}
        </p>
      )}
    </form>
  );
}
