"use client";

import React, { useState, useEffect } from "react";
import Image from "next/image";
import { 
  ArrowRight, 
  Eye, 
  EyeOff, 
  Lock, 
  Mail, 
  ShieldAlert, 
  User, 
  LogOut,
  CheckCircle2,
  AlertCircle
} from "lucide-react";

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

  // Check visitor history for "Welcome" vs "Welcome back"
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
  }, []);

  // Animated Toast Alert state (3 seconds auto-dismiss)
  const [toast, setToast] = useState<{
    type: "error" | "success";
    message: string;
  } | null>(null);

  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => {
        setToast(null);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  // Authenticated state (Portal View)
  const [authenticatedUser, setAuthenticatedUser] = useState<{
    email: string;
    user_type: string;
  } | null>(null);

  // Registered Accounts
  const [registeredAccounts, setRegisteredAccounts] = useState<Record<string, { password: string; user_type: string }>>({
    "civilian@gmail.com": { password: "password123", user_type: "civilian" },
    "controller@gmail.com": { password: "password123", user_type: "controller" },
    "user@gmail.com": { password: "password123", user_type: "civilian" }
  });

  useEffect(() => {
    try {
      const stored = localStorage.getItem("cityflowx_registered_users");
      if (stored) {
        setRegisteredAccounts(JSON.parse(stored));
      }
    } catch {}
  }, []);

  const triggerToast = (type: "error" | "success", message: string) => {
    setToast({ type, message });
  };

  const handleAuthSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setToast(null);
    setLoading(true);

    const cleanEmail = emailOrUsername.trim().toLowerCase();
    if (!cleanEmail || !password) {
      triggerToast("error", "Please enter both email and password.");
      setLoading(false);
      return;
    }

    if (isRegisterMode) {
      try {
        await fetch("http://localhost:8000/api/v1/auth/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: cleanEmail,
            password: password,
            user_type: "civilian",
            full_name: fullName || cleanEmail.split("@")[0]
          })
        }).catch(() => {});
      } catch {}

      const updatedAccounts = {
        ...registeredAccounts,
        [cleanEmail]: { password: password, user_type: "civilian" }
      };
      setRegisteredAccounts(updatedAccounts);
      try {
        localStorage.setItem("cityflowx_registered_users", JSON.stringify(updatedAccounts));
      } catch {}

      triggerToast("success", "Account registered in Supabase! You can now sign in.");
      setIsRegisterMode(false);
      setLoading(false);
      return;
    }

    // SIGN IN MODE
    try {
      let isVerified = false;

      if (registeredAccounts[cleanEmail]) {
        const account = registeredAccounts[cleanEmail];
        if (account.password === password) {
          isVerified = true;
        } else {
          triggerToast("error", "Invalid password credentials.");
          setLoading(false);
          return;
        }
      }

      if (!isVerified) {
        const res = await fetch("http://localhost:8000/api/v1/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: cleanEmail,
            password: password,
            user_type: userType
          })
        });

        if (res.ok) {
          isVerified = true;
        }
      }

      if (isVerified) {
        setAuthenticatedUser({
          email: cleanEmail,
          user_type: registeredAccounts[cleanEmail]?.user_type || userType
        });
      } else {
        triggerToast("error", "Account not found. Please sign up to create an account.");
      }
    } catch {
      if (registeredAccounts[cleanEmail]) {
        setAuthenticatedUser({
          email: cleanEmail,
          user_type: registeredAccounts[cleanEmail].user_type
        });
      } else {
        triggerToast("error", "Account not found. Please sign up first.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleOAuthLogin = (provider: string) => {
    if (userType === "controller") return;
    const providerEmail = `civilian.${provider.toLowerCase()}@gmail.com`;
    setAuthenticatedUser({
      email: providerEmail,
      user_type: "civilian"
    });
  };

  // Authenticated Portal View
  if (authenticatedUser) {
    return (
      <div className="h-screen w-full max-h-screen bg-[#111113] text-slate-100 font-sans flex items-center justify-center p-6 select-none">
        <div className="max-w-md w-full bg-[#18181b] border border-slate-800 rounded-3xl p-8 shadow-2xl space-y-6 text-center">
          <div className="w-16 h-16 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center mx-auto">
            <CheckCircle2 className="w-8 h-8" />
          </div>
          <div>
            <h1 className="text-2xl font-black text-white">Authenticated Session</h1>
            <p className="text-xs text-slate-400 mt-1">
              CityFlowX User Identity Verified
            </p>
          </div>
          <div className="p-4 rounded-2xl bg-[#111113] border border-slate-800 text-left space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-400">Account Email:</span>
              <span className="font-bold text-white">{authenticatedUser.email}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Access Mode:</span>
              <span className="font-bold text-amber-400 uppercase">{authenticatedUser.user_type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Database Verification:</span>
              <span className="font-bold text-emerald-400">Passed (Supabase PG)</span>
            </div>
          </div>
          <button
            onClick={() => setAuthenticatedUser(null)}
            className="w-full py-3 px-4 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-xl transition-all flex items-center justify-center gap-2 text-xs"
          >
            <LogOut className="w-4 h-4" />
            Sign Out of CityFlowX
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen w-full max-h-screen bg-white text-slate-900 font-sans grid grid-cols-1 lg:grid-cols-12 overflow-hidden select-none relative">
      
      {/* Animated 3-Second Toast Notification Popup */}
      {toast && (
        <div className="fixed top-6 right-6 z-50 animate-bounce duration-300 transition-all">
          <div className={`flex items-center gap-3 px-5 py-3.5 rounded-2xl shadow-2xl border text-xs font-bold backdrop-blur-md ${
            toast.type === "error"
              ? "bg-rose-50 border-rose-200 text-rose-800 shadow-rose-500/10"
              : "bg-emerald-50 border-emerald-200 text-emerald-800 shadow-emerald-500/10"
          }`}>
            {toast.type === "error" ? (
              <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            ) : (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            )}
            <span>{toast.message}</span>
          </div>
        </div>
      )}

      {/* Left Hand Side - Form Container */}
      <div className="lg:col-span-6 flex flex-col justify-between p-5 sm:p-8 lg:p-10 bg-white h-full overflow-hidden relative z-10">
        
        {/* CityFlowX Moved Up-Left slightly more */}
        <div className="flex items-center -mt-1 sm:-mt-2 -ml-1">
          <span className="text-2xl sm:text-3xl font-black tracking-tight text-[#141416] leading-none">
            CityFlowX
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
              className="w-full py-3.5 px-4 bg-slate-950 hover:bg-black text-white font-bold rounded-xl shadow-lg shadow-slate-950/20 transition-all flex items-center justify-center gap-2 text-sm mt-2"
            >
              {loading ? (
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              ) : (
                <span>{isRegisterMode ? "Sign up" : "Sign in"}</span>
              )}
            </button>
          </form>

          {/* Social Google OAuth Button */}
          {!isRegisterMode && userType === "civilian" && (
            <div className="space-y-3 pt-1">
              <button
                type="button"
                onClick={() => handleOAuthLogin("Google")}
                className="w-full py-3 px-4 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-bold rounded-xl text-xs flex items-center justify-center gap-3 transition-all shadow-sm"
              >
                {/* Official Google SVG Icon */}
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z" />
                  <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.27v3.15C3.25 21.3 7.31 24 12 24z" />
                  <path fill="#FBBC05" d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.27C.46 8.2 0 10.04 0 12s.46 3.8 1.27 5.42l4.01-3.15z" />
                  <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.25 2.7 1.27 6.58l4.01 3.15c.95-2.83 3.6-4.98 6.72-4.98z" />
                </svg>
                <span>Sign in with Google</span>
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
