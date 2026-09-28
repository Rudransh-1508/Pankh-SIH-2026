import { redirect } from "next/navigation";

import { officialApi } from "@/lib/api";
import type { Official } from "@/lib/types";

export default async function Home() {
  const official = await officialApi<Official>("/review/me");
  redirect(official.level === "ministry" ? "/coverage" : "/review");
}
