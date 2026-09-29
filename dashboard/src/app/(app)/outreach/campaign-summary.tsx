import type { Campaign } from "@/lib/types";

const STATUS = {
  draft: { label: "Draft, not sent", tone: "bg-turmeric-mist text-ink" },
  sent: { label: "Sent", tone: "bg-leaf-mist text-leaf" },
  cancelled: { label: "Cancelled", tone: "bg-paper text-ink-soft" },
} as const;

export function where(campaign: Pick<Campaign, "state" | "district">): string {
  return campaign.district ? `${campaign.district}, ${campaign.state}` : `All of ${campaign.state}`;
}

export function channelLabel(campaign: Pick<Campaign, "channel" | "language">): string {
  return `${campaign.channel === "school" ? "Through schools" : "Directly to families"} · ${
    campaign.language === "hi" ? "Hindi" : "English"
  }`;
}

export function StatusBadge({ status }: { status: Campaign["status"] }) {
  return <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS[status].tone}`}>{STATUS[status].label}</span>;
}

export function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: "Asia/Kolkata" });
}
