"use client";

import { useActionState, useState } from "react";

import { draftCampaign, type DraftState } from "./actions";

const CHANNELS = [
  { value: "school", label: "Through schools", help: "One message to each school's nodal officer, with a list of its students." },
  { value: "family", label: "Directly to families", help: "One message to each student's parent, on the number the school recorded." },
];

const LANGUAGES = [
  { value: "hi", label: "हिन्दी" },
  { value: "en", label: "English" },
];

/** Where the official may campaign: a state to choose (ministry), districts to choose (state),
 * or a fixed district. */
export interface Scope {
  states: { state: string; districts: string[] }[];
  fixed: string | null;
}

export function DraftForm({ scope }: { scope: Scope }) {
  const [state, action, pending] = useActionState<DraftState, FormData>(draftCampaign, {});
  const [chosenState, setChosenState] = useState(scope.states[0]?.state ?? "");
  const districts = scope.states.find((s) => s.state === chosenState)?.districts ?? [];
  const select = "w-full rounded-xl border-[1.5px] border-line bg-card p-3 outline-none focus:border-peacock";
  return (
    <form action={action} className="space-y-5">
      {scope.fixed ? (
        <p className="rounded-xl bg-paper p-3 text-sm">
          Students in <span className="font-semibold">{scope.fixed}</span>
        </p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {scope.states.length > 1 && (
            <label className="block space-y-2">
              <span className="text-sm font-semibold">State</span>
              <select name="state" value={chosenState} onChange={(e) => setChosenState(e.target.value)} className={select}>
                {scope.states.map((s) => (
                  <option key={s.state}>{s.state}</option>
                ))}
              </select>
            </label>
          )}
          <label className="block space-y-2">
            <span className="text-sm font-semibold">District</span>
            <select name="district" key={chosenState} defaultValue="" className={select}>
              <option value="">All districts</option>
              {districts.map((d) => (
                <option key={d}>{d}</option>
              ))}
            </select>
          </label>
          {scope.states.length === 1 && <input type="hidden" name="state" value={chosenState} />}
        </div>
      )}
      <fieldset className="space-y-2">
        <legend className="mb-2 text-sm font-semibold">How to reach them</legend>
        {CHANNELS.map((option, index) => (
          <label
            key={option.value}
            className="flex cursor-pointer gap-3 rounded-xl border-[1.5px] border-line p-3 has-[:checked]:border-peacock has-[:checked]:bg-peacock-mist"
          >
            <input type="radio" name="channel" value={option.value} defaultChecked={index === 0} className="mt-1 accent-[#0e6f78]" />
            <span>
              <span className="block font-semibold">{option.label}</span>
              <span className="block text-sm text-ink-soft">{option.help}</span>
            </span>
          </label>
        ))}
      </fieldset>
      <fieldset>
        <legend className="mb-2 text-sm font-semibold">Language</legend>
        <div className="flex gap-2">
          {LANGUAGES.map((option, index) => (
            <label
              key={option.value}
              className="cursor-pointer rounded-full border-[1.5px] border-line px-4 py-1.5 text-sm font-semibold has-[:checked]:border-peacock has-[:checked]:bg-peacock-mist has-[:checked]:text-peacock-deep"
            >
              <input type="radio" name="language" value={option.value} defaultChecked={index === 0} className="sr-only" />
              {option.label}
            </label>
          ))}
        </div>
      </fieldset>
      {state.error && (
        <p role="alert" className="rounded-lg bg-laterite-mist px-3 py-2 text-sm text-laterite">
          {state.error}
        </p>
      )}
      <button disabled={pending} className="w-full rounded-xl bg-peacock px-4 py-3 font-semibold text-white hover:bg-peacock-deep disabled:opacity-60">
        {pending ? "Drafting…" : "Draft the messages"}
      </button>
      <p className="text-center text-xs text-ink-soft">You see every message before anything is sent.</p>
    </form>
  );
}
