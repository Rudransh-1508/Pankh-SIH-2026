"use server";

import { revalidatePath } from "next/cache";

import { ApiError, officialApi } from "@/lib/api";

export async function runCoverage(): Promise<{ error?: string }> {
  try {
    await officialApi("/ministry/coverage/runs", { method: "POST" });
  } catch (error) {
    return { error: error instanceof ApiError ? error.message : "The linkage could not be run." };
  }
  revalidatePath("/coverage");
  return {};
}
