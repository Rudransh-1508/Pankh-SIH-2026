"use client";

import { useActionState } from "react";

import { decide, type DecisionState } from "./actions";

const OPTIONS = [
  { value: "confirm", label: "Confirm", help: "The student's detail is correct. A signed proof is issued in your name." },
  { value: "reject", label: "Return to student", help: "The student must fix something. Your note is shown to them." },
  { value: "escalate", label: "Send to the next level", help: "You cannot decide with the records you have." },
];

export function DecisionForm({ id, canConfirm }: { id: string; canConfirm: boolean }) {
  const [state, action, pending] = useActionState<DecisionState, FormData>(decide.bind(null, id), {});
  return (
    <form action={action} className="space-y-4">
      <fieldset className="space-y-2">
        <legend className="mb-2 text-sm font-semibold">Decision</legend>
        {OPTIONS.filter((o) => canConfirm || o.value !== "confirm").map((option) => (
          <label
            key={option.value}
            className="flex cursor-pointer gap-3 rounded-xl border-[1.5px] border-line p-3 has-[:checked]:border-peacock has-[:checked]:bg-peacock-mist"
          >
            <input type="radio" name="decision" value={option.value} required className="mt-1 accent-[#0e6f78]" />
            <span>
              <span className="block font-semibold">{option.label}</span>
              <span className="block text-sm text-ink-soft">{option.help}</span>
            </span>
          </label>
        ))}
      </fieldset>
      <label className="block space-y-2">
        <span className="text-sm font-semibold">Note for the record</span>
        <textarea
          name="note"
          required
          rows={3}
          placeholder="What you checked, or what the student needs to do"
          className="w-full rounded-xl border-[1.5px] border-line p-3 outline-none focus:border-peacock"
        />
      </label>
      {state.error && (
        <p role="alert" className="rounded-lg bg-laterite-mist px-3 py-2 text-sm text-laterite">
          {state.error}
        </p>
      )}
      <button
        disabled={pending}
        className="w-full rounded-xl bg-peacock px-4 py-3 font-semibold text-white hover:bg-peacock-deep disabled:opacity-60"
      >
        {pending ? "Saving…" : "Save decision"}
      </button>
    </form>
  );
}
