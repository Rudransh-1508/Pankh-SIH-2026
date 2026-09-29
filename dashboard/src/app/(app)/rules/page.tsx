import Link from "next/link";

import { Card, PageHeader } from "@/components/ui";
import { officialApi, publicApi } from "@/lib/api";
import type { Official, Rules } from "@/lib/types";

import { GuidelineForm } from "./guideline-form";

export const metadata = { title: "Scheme rules" };

export default async function RulesPage() {
  const [rules, official] = await Promise.all([publicApi<Rules>("/rules"), officialApi<Official>("/review/me")]);
  return (
    <>
      <PageHeader
        title="Scheme rules"
        subtitle={`The rules Pankh applies for ${rules.academic_year_label}, each linked to the page of the official guideline it comes from.`}
      />
      {official.level === "ministry" && (
        <Card className="mb-5">
          <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="font-display text-xl font-bold">Check a new guideline</h2>
            <Link href="/rules/drafts" className="text-sm font-semibold text-peacock-deep hover:underline">
              See drafts →
            </Link>
          </div>
          <p className="mb-4 text-sm text-ink-soft">
            Pankh reads the income, marks and age figures in the PDF and sets each against the rule in force, with the sentence it
            came from. Nothing changes until you approve.
          </p>
          <GuidelineForm schemes={rules.schemes.map(({ scheme }) => ({ id: scheme.id, name: scheme.name }))} />
        </Card>
      )}
      <div className="space-y-5">
        {rules.schemes.map(({ scheme, rules: list }) => (
          <Card key={scheme.id}>
            <p className="text-xs font-semibold tracking-wide text-ink-soft uppercase">
              {scheme.provider}
              {scheme.kind === "catalogue" && " · shown to students for discovery"}
            </p>
            <h2 className="mt-1 font-display text-2xl font-bold">{scheme.name}</h2>
            <p className="mt-1 text-sm text-ink-soft">
              {scheme.summary} Applications: {scheme.system_of_record}.
            </p>
            <ol className="mt-4 divide-y divide-line">
              {list.map((rule) => (
                <li key={rule.id} className="flex flex-wrap items-baseline justify-between gap-2 py-2.5">
                  <span className="font-semibold">{rule.title}</span>
                  <a
                    href={rule.citation.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm text-peacock-deep hover:underline"
                    title={rule.citation.source_title}
                  >
                    {rule.citation.clause}, page {rule.citation.page} ↗
                  </a>
                </li>
              ))}
            </ol>
          </Card>
        ))}
      </div>
    </>
  );
}
