"use client";

import { useActionState } from "react";

import { runCoverage } from "./actions";

export function RunButton({ label = "Run linkage now" }: { label?: string }) {
  const [state, action, pending] = useActionState(runCoverage, {});
  return (
    <form action={action} className="flex items-center gap-3">
      {state.error && <span className="text-sm text-laterite">{state.error}</span>}
      <button
        disabled={pending}
        className="rounded-xl bg-peacock px-4 py-2.5 text-sm font-semibold text-white hover:bg-peacock-deep disabled:opacity-60"
      >
        {pending ? "Linking registers…" : label}
      </button>
    </form>
  );
}
