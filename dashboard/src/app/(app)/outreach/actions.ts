"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { ApiError, officialApi } from "@/lib/api";
import type { Campaign } from "@/lib/types";

export interface DraftState {
  error?: string;
}

export async function draftCampaign(_state: DraftState, form: FormData): Promise<DraftState> {
  let campaign: Campaign;
  try {
    campaign = await officialApi<Campaign>("/outreach/campaigns", {
      method: "POST",
      body: JSON.stringify({
        state: form.get("state") || null,
        district: form.get("district") || null,
        channel: form.get("channel"),
        language: form.get("language"),
      }),
    });
  } catch (error) {
    return { error: error instanceof ApiError ? error.message : "The campaign could not be drafted." };
  }
  revalidatePath("/outreach");
  redirect(`/outreach/${campaign.id}`);
}

export async function decideCampaign(id: string, decision: "send" | "cancel"): Promise<void> {
  await officialApi(`/outreach/campaigns/${id}/${decision}`, { method: "POST" });
  revalidatePath("/outreach");
  revalidatePath(`/outreach/${id}`);
}
