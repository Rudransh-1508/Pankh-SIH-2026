import Link from "next/link";

import { PageHeader, number } from "@/components/ui";
import { officialApi } from "@/lib/api";
import type { UnreachedStudent } from "@/lib/types";

export const metadata = { title: "Students not reached" };

export default async function UnreachedPage({ searchParams }: { searchParams: Promise<{ state?: string; district?: string }> }) {
  const { state, district } = await searchParams;
  const query = new URLSearchParams({ ...(state && { state }), ...(district && { district }), limit: "500" });
  const { total, items } = await officialApi<{ total: number; items: UnreachedStudent[] }>(
    `/ministry/coverage/unreached?${query}`,
  );
  const place = [district, state].filter(Boolean).join(", ") || "All states";
  return (
    <>
      <Link href="/coverage" className="text-sm font-semibold text-peacock-deep hover:underline">
        ← Coverage
      </Link>
      <PageHeader
        title={`Not reached: ${place}`}
        subtitle={`${number(total)} enrolled ST students with no scholarship registration, and what each could apply for.`}
        action={
          <a
            href={`/coverage/unreached/export?${query}`}
            className="rounded-xl border-[1.5px] border-line bg-card px-4 py-2.5 text-sm font-semibold hover:border-peacock"
          >
            Download list for outreach (CSV)
          </a>
        }
      />
      <div className="overflow-hidden rounded-2xl border-[1.5px] border-line bg-card">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line bg-paper text-xs tracking-wide text-ink-soft uppercase">
            <tr>
              <th className="px-4 py-3 font-semibold">Student</th>
              <th className="px-4 py-3 font-semibold">Class</th>
              <th className="hidden px-4 py-3 font-semibold md:table-cell">School (U-DISE)</th>
              <th className="px-4 py-3 font-semibold">Could apply for</th>
            </tr>
          </thead>
          <tbody>
            {items.map((student) => (
              <tr key={student.student_ref} className="border-b border-line last:border-0">
                <td className="px-4 py-3">
                  <p className="font-semibold">{student.name}</p>
                  <p className="text-xs text-ink-soft">{student.district}, {student.state}</p>
                </td>
                <td className="px-4 py-3 tabular">{student.class}</td>
                <td className="hidden px-4 py-3 font-mono text-xs md:table-cell">{student.udise_code}</td>
                <td className="px-4 py-3">
                  {student.likely_schemes.map((s) => (
                    <span key={s.scheme_id} className="mr-1.5 inline-flex rounded-full bg-peacock-mist px-2.5 py-0.5 text-xs font-semibold text-peacock-deep">
                      {s.scheme}
                    </span>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
