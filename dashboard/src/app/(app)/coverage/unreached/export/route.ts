import { officialApi } from "@/lib/api";
import type { UnreachedStudent } from "@/lib/types";

function cell(value: string): string {
  return /[",\n]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value;
}

/** The unreached list as CSV, for schools and field teams doing outreach. */
export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  params.set("limit", "2000");
  const { items } = await officialApi<{ items: UnreachedStudent[] }>(`/ministry/coverage/unreached?${params}`);
  const header = ["student_ref", "name", "class", "gender", "district", "state", "udise_code", "could_apply_for"];
  const rows = items.map((s) =>
    [s.student_ref, s.name, s.class, s.gender, s.district, s.state, s.udise_code, s.likely_schemes.map((x) => x.scheme).join("; ")]
      .map(cell)
      .join(","),
  );
  return new Response(`﻿${[header.join(","), ...rows].join("\n")}\n`, {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": 'attachment; filename="pankh-unreached-students.csv"',
    },
  });
}
