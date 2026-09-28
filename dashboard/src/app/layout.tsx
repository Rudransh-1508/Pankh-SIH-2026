import type { Metadata } from "next";
import { Baloo_2, Noto_Sans, Noto_Sans_Devanagari } from "next/font/google";
import "./globals.css";

const baloo = Baloo_2({ subsets: ["latin"], weight: ["600", "700"], variable: "--font-baloo" });
const notoSans = Noto_Sans({ subsets: ["latin"], variable: "--font-noto-sans" });
// Names on education registers are often written in Devanagari.
const notoDevanagari = Noto_Sans_Devanagari({ subsets: ["devanagari"], variable: "--font-noto-devanagari" });

export const metadata: Metadata = {
  title: { default: "Pankh for officials", template: "%s · Pankh" },
  description: "Review queues, coverage and application pipelines for MoTA scholarships.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${baloo.variable} ${notoSans.variable} ${notoDevanagari.variable}`}>
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
