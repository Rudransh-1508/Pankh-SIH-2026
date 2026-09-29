import { officialApi } from "@/lib/api";
import type { RuleDraft } from "@/lib/types";

/** The approved draft's parameter file, named for its place in the rules repository. */
export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const drafts = await officialApi<RuleDraft[]>("/ministry/rule-drafts");
  const draft = drafts.find((d) => d.id === id);
  if (!draft) return new Response("No such draft.", { status: 404 });
  const text = await officialApi<string>(`/ministry/rule-drafts/${id}/patch`, {
    headers: { Accept: "text/plain" },
  });
  const path = `rules/pankh_rules/parameters/${draft.parameter.replaceAll(".", "/")}.yaml`;
  return new Response(text, {
    headers: {
      "Content-Type": "text/yaml; charset=utf-8",
      "Content-Disposition": `attachment; filename="${path.split("/").slice(-2).join("_")}"`,
    },
  });
}
