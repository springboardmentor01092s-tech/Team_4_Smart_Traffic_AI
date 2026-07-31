import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get("code");

  let userEmail = "";
  let userName = "";

  if (code) {
    const cookieStore = await cookies();

    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || "https://placeholder.supabase.co";
    const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "placeholder-anon-key";

    const supabase = createServerClient(
      supabaseUrl,
      supabaseAnonKey,
      {
        cookies: {
          get(name) {
            return cookieStore.get(name)?.value;
          },
          set(name, value, options) {
            cookieStore.set({ name, value, ...options });
          },
          remove(name, options) {
            cookieStore.set({ name, value: "", ...options });
          },
        },
      }
    );

    const { data: sessionData } = await supabase.auth.exchangeCodeForSession(code);
    if (sessionData?.user?.email) {
      userEmail = sessionData.user.email;
      userName = sessionData.user.user_metadata?.full_name || sessionData.user.user_metadata?.name || userEmail.split("@")[0];

      try {
        const backendUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";
        await fetch(`${backendUrl}/auth/google-sync`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: userEmail,
            full_name: userName,
            user_type: "civilian",
          }),
        });
      } catch (err) {
        console.error("Failed to sync Google user to database:", err);
      }
    }
  }

  const redirectUrl = new URL("/", request.url);
  redirectUrl.searchParams.set("auth", "google_success");
  if (userEmail) redirectUrl.searchParams.set("email", userEmail);
  if (userName) redirectUrl.searchParams.set("name", userName);

  return NextResponse.redirect(redirectUrl);
}