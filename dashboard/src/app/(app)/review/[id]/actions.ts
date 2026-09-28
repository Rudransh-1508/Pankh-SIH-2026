"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { ApiError, officialApi } from "@/lib/api";

export interface DecisionState {
  error?: string;
}

export async function decide(id: string, _state: DecisionState, form: FormData): Promise<DecisionState> {
  try {
    await officialApi(`/review/exceptions/${id}/decision`, {
      method: "POST",
      body: JSON.stringify({ decision: form.get("decision"), note: form.get("note") }),
    });
  } catch (error) {
    return { error: error instanceof ApiError ? error.message : "The decision could not be saved." };
  }
  revalidatePath("/review");
  redirect("/review");
}
