"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { ApiError, officialApi } from "@/lib/api";

export interface FormState {
  error?: string;
}

export async function checkGuideline(_state: FormState, form: FormData): Promise<FormState> {
  const file = form.get("file");
  if (!(file instanceof File) || file.size === 0) return { error: "Choose the guideline PDF." };
  const body = new FormData();
  body.set("scheme_id", String(form.get("scheme_id")));
  body.set("title", String(form.get("title")));
  body.set("file", file);
  try {
    await officialApi("/ministry/rule-drafts", { method: "POST", body });
  } catch (error) {
    return {
      error: error instanceof ApiError ? error.message : "The guideline could not be checked.",
    };
  }
  revalidatePath("/rules/drafts");
  redirect("/rules/drafts");
}

export async function decideDraft(id: string, _state: FormState, form: FormData): Promise<FormState> {
  try {
    await officialApi(`/ministry/rule-drafts/${id}/decision`, {
      method: "POST",
      body: JSON.stringify({
        decision: form.get("decision"),
        effective_from: form.get("effective_from") || null,
        note: form.get("note") ?? "",
      }),
    });
  } catch (error) {
    return {
      error: error instanceof ApiError ? error.message : "The decision could not be saved.",
    };
  }
  revalidatePath("/rules/drafts");
  return {};
}
