"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { ApiError, publicApi, SESSION_COOKIE } from "@/lib/api";

export interface LoginState {
  step: "phone" | "code";
  phone?: string;
  error?: string;
  /** Only on a demo deployment, for the demo officials' numbers. */
  demoCode?: string;
}

export async function signIn(state: LoginState, form: FormData): Promise<LoginState> {
  if (state.step === "phone") {
    try {
      const sent = await publicApi<{ phone: string; demo_code?: string }>("/auth/otp/request", {
        method: "POST",
        body: JSON.stringify({ phone: String(form.get("phone") ?? "") }),
      });
      return { step: "code", phone: sent.phone, demoCode: sent.demo_code };
    } catch (error) {
      return { step: "phone", error: error instanceof ApiError ? error.message : "Could not send the code." };
    }
  }
  let tokens: { access_token: string; expires_in: number };
  try {
    tokens = await publicApi("/auth/otp/verify", {
      method: "POST",
      body: JSON.stringify({ phone: state.phone, code: String(form.get("code") ?? ""), role: "official" }),
    });
  } catch (error) {
    return { ...state, error: error instanceof ApiError ? error.message : "Could not sign in." };
  }
  (await cookies()).set(SESSION_COOKIE, tokens.access_token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: tokens.expires_in,
  });
  redirect("/");
}

export async function signOut() {
  (await cookies()).delete(SESSION_COOKIE);
  redirect("/login");
}
