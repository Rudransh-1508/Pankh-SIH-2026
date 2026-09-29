"use server";

import { revalidatePath } from "next/cache";

import { officialApi } from "@/lib/api";

export async function decideReminder(id: string, decision: "approve" | "dismiss") {
  await officialApi(`/review/nudges/${id}/decision`, { method: "POST", body: JSON.stringify({ decision }) });
  revalidatePath("/reminders");
}

export async function sweep(): Promise<void> {
  await officialApi("/ministry/chasing/sweep", { method: "POST" });
  revalidatePath("/reminders");
}
