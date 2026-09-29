"use server";

import { revalidatePath } from "next/cache";

import { officialApi } from "@/lib/api";

export async function decideFacilitator(id: string, decision: "approve" | "reject"): Promise<void> {
  await officialApi(`/review/facilitators/${id}/decision`, { method: "POST", body: JSON.stringify({ decision }) });
  revalidatePath("/facilitators");
}
