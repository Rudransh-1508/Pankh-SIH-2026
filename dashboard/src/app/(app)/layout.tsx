import Image from "next/image";

import { signOut } from "@/app/login/actions";
import { Nav } from "@/components/nav";
import { officialApi } from "@/lib/api";
import type { Official } from "@/lib/types";

const LEVEL_LABELS = { institute: "Institute", district: "District", state: "State", ministry: "Ministry" };

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const official = await officialApi<Official>("/review/me");
  const seesCoverage = official.level === "ministry" || official.level === "state";
  const items = [
    { href: "/review", label: "Review queue" },
    ...(seesCoverage
      ? [
          { href: "/coverage", label: "Coverage" },
          { href: "/pipeline", label: "Pipeline" },
        ]
      : []),
    { href: "/rules", label: "Scheme rules" },
  ];
  const place = [official.district, official.state].filter(Boolean).join(", ") || "All of India";
  return (
    <div className="lg:grid lg:min-h-screen lg:grid-cols-[260px_1fr]">
      <aside className="flex flex-col gap-4 border-b border-line bg-card p-5 lg:gap-6 lg:border-r lg:border-b-0">
        <div className="flex items-center gap-3">
          <Image src="/pankh-icon.png" alt="" width={40} height={40} className="rounded-xl" />
          <p className="font-display text-xl font-bold text-peacock-deep">Pankh</p>
          <form action={signOut} className="ml-auto lg:hidden">
            <button className="text-sm font-semibold text-peacock-deep hover:underline">Sign out</button>
          </form>
        </div>
        <Nav items={items} />
        <div className="hidden space-y-3 border-t border-line pt-4 lg:mt-auto lg:block">
          <div>
            <p className="text-sm font-semibold">{official.name}</p>
            <p className="text-xs text-ink-soft">
              {LEVEL_LABELS[official.level]} · {place}
            </p>
          </div>
          <form action={signOut}>
            <button className="text-sm font-semibold text-peacock-deep hover:underline">Sign out</button>
          </form>
        </div>
      </aside>
      <main className="mx-auto w-full max-w-6xl px-5 py-8 lg:px-10">{children}</main>
    </div>
  );
}
