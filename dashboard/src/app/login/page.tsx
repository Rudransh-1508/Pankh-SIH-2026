import Image from "next/image";

import { LoginForm } from "./login-form";

export const metadata = { title: "Sign in" };

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ expired?: string }> }) {
  const { expired } = await searchParams;
  return (
    <main className="grid min-h-screen lg:grid-cols-[1.1fr_1fr]">
      <section className="relative hidden flex-col justify-between overflow-hidden bg-ink p-12 text-white lg:flex">
        <p className="font-display text-2xl font-bold tracking-wide text-turmeric">Pankh</p>
        <div className="max-w-md space-y-5">
          <Image src="/pankh-icon.png" alt="" width={112} height={112} priority className="rounded-3xl" />
          <h1 className="font-display text-4xl leading-tight font-bold">
            Every eligible ST student, reached and paid on time.
          </h1>
          <p className="text-lg text-white/70">
            Review queues for your jurisdiction, coverage of enrolled students, and where applications stall.
          </p>
        </div>
        <p className="text-sm text-white/50">Ministry of Tribal Affairs scholarships · for officials</p>
      </section>
      <section className="flex items-center justify-center px-5 py-12">
        <div className="w-full max-w-sm space-y-8">
          <div className="space-y-2">
            <div className="mb-6 flex items-center gap-3 lg:hidden">
              <Image src="/pankh-icon.png" alt="" width={44} height={44} className="rounded-xl" />
              <p className="font-display text-2xl font-bold text-peacock-deep">Pankh</p>
            </div>
            <h2 className="font-display text-3xl font-bold">Sign in</h2>
            <p className="text-ink-soft">Use the mobile number registered for your office.</p>
          </div>
          {expired && (
            <p className="rounded-lg bg-turmeric-mist px-3 py-2 text-sm">Your session ended. Sign in again.</p>
          )}
          <LoginForm />
        </div>
      </section>
    </main>
  );
}
