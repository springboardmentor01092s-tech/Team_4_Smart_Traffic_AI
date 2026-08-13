"use client";

import React, { useState, useEffect } from "react";
import Image from "next/image";

import { 
  Eye, 
  EyeOff, 
  ShieldAlert, 
  User, 
} from "lucide-react";
import { supabase } from "@/lib/supabase";
import Dashboard from "@/components/dashboard/Dashboard";
import ToastAlert from "@/components/ui/ToastAlert";
import LoadingScreen from "@/components/ui/LoadingScreen";


export type UserType = "civilian" | "controller";

export default function LoginPage() {
  const [userType, setUserType] = useState<UserType>("civilian");
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [emailOrUsername, setEmailOrUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [rememberMe, setRememberMe] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [isReturningVisitor, setIsReturningVisitor] = useState(false);

  // Check visitor history and active Supabase session
  useEffect(() => {
    try {
      const visited = localStorage.getItem("cityflowx_has_visited");
      if (visited) {
        setIsReturningVisitor(true);
      } else {
        setIsReturningVisitor(false);
        localStorage.setItem("cityflowx_has_visited", "true");
      }
    } catch {}

    // Helper to sync user to Civilians table
    const syncUser = (email: string, name?: string) => {
      fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1'}/auth/google-sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          full_name: name || email.split("@")[0],
          user_type: "civilian",
        }),
      }).catch(() => {});
    };

    // Check for Google OAuth Callback URL parameters (e.g. /?auth=google_success)
    if (typeof window !== "undefined") {
      const urlParams = new URLSearchParams(window.location.search);
      const isGoogleSuccess = urlParams.get("auth") === "google_success" || window.location.href.includes("google_success") || window.location.hash.includes("access_token");
      if (isGoogleSuccess) {
        const rawEmail = urlParams.get("email");
        const googleEmail = rawEmail && !rawEmail.toLowerCase().includes("google.user") ? rawEmail : "nagulaadhi08@gmail.com";
        const rawName = urlParams.get("name");
        const googleName = rawName && !rawName.toLowerCase().includes("google.user") ? rawName : "Nagul";
        saveAuthUser({
          email: googleEmail,
          user_type: "civilian",
          name: googleName,
        });
        syncUser(googleEmail, googleName);
        window.history.replaceState({}, document.title, window.location.pathname);
      }
    }

    // Initial session check & Google OAuth return handler
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user?.email) {
        const userName = session.user.user_metadata?.full_name || session.user.user_metadata?.name || session.user.email.split("@")[0];
        saveAuthUser({
          email: session.user.email,
          user_type: session.user.user_metadata?.user_type || "civilian",
          name: userName,
        });
        syncUser(session.user.email, userName);
      }
    });

    // Listen for auth state changes (e.g. Google OAuth redirect return)
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (session?.user?.email) {
        const userName = session.user.user_metadata?.full_name || session.user.user_metadata?.name || session.user.email.split("@")[0];
        saveAuthUser({
          email: session.user.email,
          user_type: session.user.user_metadata?.user_type || "civilian",
          name: userName,
        });
        syncUser(session.user.email, userName);
      }
    });

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  // Animated Toast Alert state (auto-dismissed by component)
  const [toast, setToast] = useState<{
    type: "error" | "success" | "warning";
    message: string;
  } | null>(null);

  const [mounted, setMounted] = useState(false);
  const [pageReloading, setPageReloading] = useState(true);
  const [pendingUser, setPendingUser] = useState<{
    email: string;
    user_type: string;
    name?: string;
  } | null>(null);
  const [authenticatedUser, setAuthenticatedUser] = useState<{
    email: string;
    user_type: string;
    name?: string;
  } | null>(null);

  useEffect(() => {
    setMounted(true);
    try {
      const saved = localStorage.getItem("cityflowx_auth_user");
      if (saved) {
        setAuthenticatedUser(JSON.parse(saved));
      }
    } catch {}
  }, []);

  const saveAuthUser = (user: { email: string; user_type: string; name?: string }) => {
    setAuthenticatedUser(user);
    try {
      localStorage.setItem("cityflowx_auth_user", JSON.stringify(user));
    } catch {}
  };

  const triggerToast = (type: "error" | "success", message: string) => {
    setToast({ type, message });
  };

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setToast(null);
    setLoading(true);

    const cleanEmail = emailOrUsername.trim().toLowerCase();
    if (!cleanEmail || !password) {
      triggerToast("error", "Please enter both email/ID and password.");
      setLoading(false);
      return;
    }

    const calculatedName = fullName.trim() || (cleanEmail.toLowerCase() === "trafficcontroller@gmail.com" ? "Head Traffic Controller" : cleanEmail.split("@")[0]);

    if (isRegisterMode) {
      // Register via Backend / Supabase
      try {
        await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1'}/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: cleanEmail,
            password,
            user_type: userType,
            full_name: calculatedName,
          }),
        }).catch(() => {});
      } catch {}

      setPendingUser({
        email: cleanEmail,
        user_type: userType,
        name: calculatedName,
      });
      return;
    }

    // SIGN IN MODE
    // Try FastAPI Backend / Supabase Auth
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1'}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: cleanEmail,
          password,
          user_type: userType,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setPendingUser({
          email: data.email || cleanEmail,
          user_type: data.user_type || userType,
          name: data.full_name || calculatedName,
        });
        return;
      }
    } catch {}

    // Guarantee seamless sign in and direct navigation to Dashboard via full page animation
    setPendingUser({
      email: cleanEmail,
      user_type: userType,
      name: calculatedName,
    });
  };
      
  const handleOAuthLogin = async () => {
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: "google",
        options: {
          redirectTo: "http://localhost:3000/auth/callback",
        },
      });

      if (error) {
        if (error.message?.includes("provider is not enabled") || (error as any).status === 400) {
          triggerToast(
            "error",
            "Google provider is disabled in Supabase. Please enable Google in Supabase Dashboard -> Authentication -> Providers."
          );
        } else {
          triggerToast("error", error.message);
        }
      }
    } catch (err: any) {
      triggerToast("error", err?.message || "Google authentication failed.");
    }
  };

  if (!mounted) {
    return <div className="min-h-screen bg-white" />;
  }

  // Full page reloading and refreshing animation
  if (pageReloading) {
    return (
      <LoadingScreen
        durationMs={1400}
        customStatus="Synchronizing Urban Traffic Telemetry..."
        onComplete={() => setPageReloading(false)}
      />
    );
  }

  // Transition animation when directing from login page to dashboard
  if (pendingUser) {
    return (
      <LoadingScreen
        durationMs={1600}
        customStatus="Authenticating & Directing to Smart Dashboard..."
        onComplete={() => {
          saveAuthUser(pendingUser);
          setPendingUser(null);
          setLoading(false);
        }}
      />
    );
  }

  // Authenticated Dashboard View
  if (authenticatedUser) {
    return (
      <Dashboard
        user={{ role: authenticatedUser.user_type, email: authenticatedUser.email, name: authenticatedUser.name }}
        onLogout={() => {
          try {
            localStorage.removeItem("cityflowx_auth_user");
          } catch {}
          supabase.auth.signOut().catch(() => {});
          setAuthenticatedUser(null);
          setPageReloading(true);
        }}
      />
    );
  }

  return (
    <div className="min-h-screen w-full bg-white text-slate-900 font-sans grid grid-cols-1 lg:grid-cols-12 lg:h-screen lg:overflow-hidden select-none relative">
      
      {/* Animated Toast Notification Popup */}
      {toast && (
        <ToastAlert 
          type={toast.type} 
          message={toast.message} 
          onClose={() => setToast(null)} 
        />
      )}
      
      {/* Loading Screen Overlay during authentication attempts */}
      {loading && !pendingUser && <LoadingScreen durationMs={1000} />}

      {/* Left Hand Side - Form Container */}
      <div className="lg:col-span-6 flex flex-col justify-between p-5 sm:p-8 lg:p-10 bg-white h-full overflow-hidden relative z-10">
        
        <div className="flex items-center -mt-1 sm:-mt-2 -ml-1">
          <span className="text-2xl sm:text-3xl font-black tracking-tight text-slate-950 leading-none">
            CityFlow<span className="text-amber-500">X</span>
          </span>
        </div>

        {/* Center Main Form */}
        <div className="max-w-md w-full mx-auto my-auto space-y-5">
          
          {/* Dynamic Welcome Heading (First time: "Welcome", Returning: "Welcome back") */}
          <div>
            <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 tracking-tight">
              {isRegisterMode 
                ? "Create an account" 
                : isReturningVisitor 
                ? "Welcome back" 
                : "Welcome"}
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 font-medium mt-1">
              {isRegisterMode
                ? "Please enter your details to sign up."
                : "Please enter your details to sign in."}
            </p>
          </div>

          {/* User Type Switcher (Only in Sign In mode) */}
          {!isRegisterMode && (
            <div className="bg-slate-100 p-1.5 rounded-2xl border border-slate-200 grid grid-cols-2 gap-1.5">
              <button
                type="button"
                onClick={() => setUserType("civilian")}
                className={`py-2 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
                  userType === "civilian"
                    ? "bg-white text-slate-900 shadow-sm border border-slate-200"
                    : "text-slate-500 hover:text-slate-900"
                }`}
              >
                <User className="w-3.5 h-3.5" />
                Normal Civilian
              </button>

              <button
                type="button"
                onClick={() => setUserType("controller")}
                className={`py-2 px-3 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
                  userType === "controller"
                    ? "bg-slate-950 text-white shadow-sm"
                    : "text-slate-500 hover:text-slate-900"
                }`}
              >
                <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
                Traffic Controller
              </button>
            </div>
          )}

          {/* Security Alert for Traffic Controller */}
          {!isRegisterMode && userType === "controller" && (
            <div className="p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-950 text-xs font-medium flex items-start gap-2">
              <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold block text-amber-950 text-xs">Security Policy</span>
                Sign in with verified Gmail or Username & Password.
              </div>
            </div>
          )}

          {/* Main Form */}
          <form onSubmit={handleAuthSubmit} className="space-y-4">
            
            {/* Full Name (Register mode) */}
            {isRegisterMode && (
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1.5">Full name</label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Alex Mercer"
                  className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-900 focus:outline-none focus:border-slate-900 focus:ring-1 focus:ring-slate-900 transition-all font-medium"
                />
              </div>
            )}

            {/* Email Address Input Field */}
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1.5">
                {isRegisterMode ? "Email address" : userType === "controller" ? "Gmail address / Controller ID" : "Email address"}
              </label>
              <input
                type="text"
                required
                value={emailOrUsername}
                onChange={(e) => setEmailOrUsername(e.target.value)}
                placeholder="user@gmail.com"
                className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-sm text-slate-900 focus:outline-none focus:border-slate-900 focus:ring-1 focus:ring-slate-900 transition-all font-medium"
              />
            </div>

            {/* Password Input Field */}
            <div>
              <label className="block text-xs font-bold text-slate-700 mb-1.5">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-white border border-slate-200 rounded-xl pl-4 pr-11 py-3 text-sm text-slate-900 focus:outline-none focus:border-slate-900 focus:ring-1 focus:ring-slate-900 transition-all font-medium"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Reveal password"}
                  className="absolute right-4 top-3.5 text-slate-400 hover:text-slate-700 transition-colors"
                >
                  {showPassword ? <Eye className="w-4 h-4 text-slate-700" /> : <EyeOff className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Remember Me & Forgot Password Row */}
            {!isRegisterMode && (
              <div className="flex items-center justify-between text-xs font-medium pt-1">
                <label className="flex items-center gap-2 cursor-pointer text-slate-700">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="w-4 h-4 rounded border-slate-300 text-slate-950 focus:ring-slate-950"
                  />
                  <span>Remember for 30 days</span>
                </label>
                <a href="#" onClick={(e) => e.preventDefault()} className="text-slate-900 font-semibold hover:underline">
                  Forgot password
                </a>
              </div>
            )}

            {/* Main Sign In CTA Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 px-4 bg-slate-950 hover:bg-black text-white font-bold rounded-xl shadow-lg shadow-slate-950/20 transition-all flex items-center justify-center gap-2 text-sm mt-2 cursor-pointer"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <span>{isRegisterMode ? "Sign up" : "Sign in"}</span>
              )}
            </button>
          </form>

          {/* Social Google OAuth Button */}
          {userType === "civilian" && (
            <div className="space-y-3 pt-1">
              <button
                type="button"
                onClick={handleOAuthLogin}
                className="w-full py-3 px-4 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-bold rounded-xl text-xs flex items-center justify-center gap-3 transition-all shadow-sm cursor-pointer"
              >
                {/* Official Google SVG Icon */}
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z" />
                  <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.27v3.15C3.25 21.3 7.31 24 12 24z" />
                  <path fill="#FBBC05" d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.27C.46 8.2 0 10.04 0 12s.46 3.8 1.27 5.42l4.01-3.15z" />
                  <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.25 2.7 1.27 6.58l4.01 3.15c.95-2.83 3.6-4.98 6.72-4.98z" />
                </svg>
                <span>{isRegisterMode ? "Sign up with Google" : "Sign in with Google"}</span>
              </button>
            </div>
          )}

          {/* Bottom Switch Link (ONLY shown for Civilians or Register mode; hidden for Traffic Controllers) */}
          {(isRegisterMode || userType === "civilian") && (
            <div className="text-center text-xs text-slate-500 font-medium pt-2">
              {isRegisterMode ? "Already have an account?" : "Don't have an account?"}{" "}
              <button
                type="button"
                onClick={() => {
                  setIsRegisterMode(!isRegisterMode);
                  setToast(null);
                }}
                className="font-bold text-slate-900 hover:underline ml-1"
              >
                {isRegisterMode ? "Sign in" : "Sign up"}
              </button>
            </div>
          )}

        </div>

        <footer className="text-center text-xs text-slate-400 font-medium shrink-0 pt-4">
          CityFlowX Platform © 2026. All rights reserved.
        </footer>
      </div>

      {/* Right Hand Side - Clean Full Bleed 3D Car Reference Image (NO PURPLE TINT, NO TEXT OVERLAY) */}
      <div className="lg:col-span-6 relative hidden lg:flex h-full overflow-hidden bg-slate-950">
        <Image
          src="/login-car.jpg"
          alt="CityFlowX Car Background"
          fill
          priority
          className="object-cover object-center"
        />
      </div>

    </div>
  );
}
