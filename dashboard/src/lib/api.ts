import "server-only";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export const SESSION_COOKIE = "pankh_official";
const API_URL = process.env.PANKH_API_URL ?? "http://localhost:8000/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function call<T>(path: string, init: RequestInit & { token?: string } = {}): Promise<T> {
  const { token, ...rest } = init;
  const response = await fetch(`${API_URL}${path}`, {
    ...rest,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...rest.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = typeof body.detail === "string" ? body.detail : `Request failed (${response.status})`;
    throw new ApiError(detail, response.status);
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

/** An API call as the signed-in official. Sends them to sign in if their session has ended. */
export async function officialApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) redirect("/login");
  try {
    return await call<T>(path, { ...init, token });
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) redirect("/login?expired=1");
    throw error;
  }
}

/** An API call that needs no sign-in. */
export function publicApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  return call<T>(path, init);
}

/** The API's origin, for paths the API returns whole (such as signed document links). */
export const API_ORIGIN = new URL(API_URL).origin;
