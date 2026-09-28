import { NextResponse, type NextRequest } from "next/server";

/** Optimistic check only: pages still verify the session with the API on every request. */
export function proxy(request: NextRequest) {
  if (!request.cookies.has("pankh_official")) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  return NextResponse.next();
}

export const config = {
  // Everything except sign-in, Next's own files and static files (any path with a dot).
  matcher: ["/((?!login|_next|.*\\..*).*)"],
};
