"use client";

import { useActionState } from "react";

import { checkGuideline, type FormState } from "./actions";

export function GuidelineForm({ schemes }: { schemes: { id: string; name: string }[] }) {
  const [state, action, pending] = useActionState<FormState, FormData>(checkGuideline, {});
  const field = "w-full rounded-xl border-[1.5px] border-line bg-card p-3 outline-none focus:border-peacock";
  return (
    <form action={action} className="grid gap-3 sm:grid-cols-2">
      <label className="block space-y-2">
        <span className="text-sm font-semibold">Scheme</span>
        <select name="scheme_id" className={field}>
          {schemes.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </label>
      <label className="block space-y-2">
        <span className="text-sm font-semibold">Guideline title</span>
        <input name="title" required minLength={3} placeholder="e.g. Revised guidelines, 2027" className={field} />
      </label>
      <label className="block space-y-2 sm:col-span-2">
        <span className="text-sm font-semibold">Guideline PDF</span>
        <input
          name="file"
          type="file"
          accept="application/pdf"
          required
          className="block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-peacock-mist file:px-4 file:py-2 file:font-semibold file:text-peacock-deep"
        />
      </label>
      {state.error && (
        <p role="alert" className="rounded-lg bg-laterite-mist px-3 py-2 text-sm text-laterite sm:col-span-2">
          {state.error}
        </p>
      )}
      <div className="sm:col-span-2">
        <button
          disabled={pending}
          className="rounded-xl bg-peacock px-5 py-3 font-semibold text-white hover:bg-peacock-deep disabled:opacity-60"
        >
          {pending ? "Reading the guideline…" : "Check against the rules"}
        </button>
      </div>
    </form>
  );
}
