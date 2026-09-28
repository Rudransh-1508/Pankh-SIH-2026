import { Card, PageHeader } from "@/components/ui";
import { publicApi } from "@/lib/api";
import type { Rules } from "@/lib/types";

export const metadata = { title: "Scheme rules" };

export default async function RulesPage() {
  const rules = await publicApi<Rules>("/rules");
  return (
    <>
      <PageHeader
        title="Scheme rules"
        subtitle={`The rules Pankh applies for ${rules.academic_year_label}, each linked to the page of the official guideline it comes from.`}
      />
      <div className="space-y-5">
        {rules.schemes.map(({ scheme, rules: list }) => (
          <Card key={scheme.id}>
            <h2 className="font-display text-2xl font-bold">{scheme.name}</h2>
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
