import { API_ORIGIN, officialApi } from "@/lib/api";
import type { Case } from "@/lib/types";

/** The case's photo, fetched through a fresh link signed for this official and never cached. */
export async function GET(_request: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const item = await officialApi<Case>(`/review/exceptions/${id}`);
  if (!item.photo?.url) return new Response("This photo has been deleted.", { status: 410 });
  const photo = await fetch(`${API_ORIGIN}${item.photo.url}`, { cache: "no-store" });
  if (!photo.ok) return new Response("The photo could not be loaded.", { status: photo.status });
  return new Response(photo.body, {
    headers: {
      "Content-Type": item.photo.content_type,
      "Cache-Control": "private, no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
