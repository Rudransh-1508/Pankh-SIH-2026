"use client";

import { useActionState, useSyncExternalStore } from "react";

import { signIn, type LoginState } from "./actions";

const field =
  "w-full rounded-xl border-[1.5px] border-line bg-card px-4 py-3.5 text-lg tabular outline-none focus:border-peacock";

export function LoginForm() {
  const [state, action, pending] = useActionState<LoginState, FormData>(signIn, { step: "phone" });
  // Until the page is interactive a tap would post the form twice; wait for it.
  const ready = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false,
  );
  const readable = state.phone?.replace(/^\+91(\d{5})(\d{5})$/, "+91 $1 $2");
  return (
    <form action={action} className="space-y-5">
      {state.step === "phone" ? (
        <label className="block space-y-2">
          <span className="text-sm font-semibold text-ink-soft">Registered mobile number</span>
          <input name="phone" inputMode="tel" autoComplete="tel-national" required placeholder="98765 43210" className={field} />
        </label>
      ) : (
        <label className="block space-y-2">
          <span className="text-sm font-semibold text-ink-soft">6-digit code sent to {readable}</span>
          <input
            name="code"
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="\d{6}"
            maxLength={6}
            required
            autoFocus
            className={`${field} tracking-[0.5em]`}
          />
        </label>
      )}
      {state.demoCode && (
        <p className="rounded-lg bg-turmeric-mist px-3 py-2 text-sm">
          Demo: no SMS is sent to demo numbers. Your code is <span className="font-semibold tabular">{state.demoCode}</span>.
        </p>
      )}
      {state.error && (
        <p role="alert" className="rounded-lg bg-laterite-mist px-3 py-2 text-sm text-laterite">
          {state.error}
        </p>
      )}
      <button
        disabled={pending || !ready}
        className="w-full rounded-xl bg-peacock px-4 py-3.5 text-base font-semibold text-white transition hover:bg-peacock-deep disabled:opacity-60"
      >
        {pending ? "Please wait…" : state.step === "phone" ? "Send code" : "Sign in"}
      </button>
    </form>
  );
}
