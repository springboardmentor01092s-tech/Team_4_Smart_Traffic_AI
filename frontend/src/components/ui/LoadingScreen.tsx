"use client";

import React, { useEffect, useState } from "react";

interface LoadingScreenProps {
  onComplete?: () => void;
  durationMs?: number;
}

export default function LoadingScreen({ onComplete, durationMs = 1800 }: LoadingScreenProps) {
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState("Initializing CityFlowX AI...");
  const [isFadingOut, setIsFadingOut] = useState(false);

  useEffect(() => {
    const startTime = Date.now();

    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const pct = Math.min(100, Math.floor((elapsed / durationMs) * 100));
      setProgress(pct);

      if (pct < 35) {
        setStatusText("Initializing CityFlowX AI Engine...");
      } else if (pct < 70) {
        setStatusText("Connecting to Supabase PostgreSQL Telemetry...");
      } else if (pct < 95) {
        setStatusText("Synchronizing Urban Signal Matrix...");
      } else {
        setStatusText("System Ready");
      }

      if (pct >= 100) {
        clearInterval(interval);
        setIsFadingOut(true);
        setTimeout(() => {
          if (onComplete) onComplete();
        }, 400);
      }
    }, 30);

    return () => clearInterval(interval);
  }, [durationMs, onComplete]);

  return (
    <div
      className={`fixed inset-0 z-50 bg-[#121118] text-white flex flex-col items-center justify-center p-6 select-none transition-opacity duration-500 ease-out ${
        isFadingOut ? "opacity-0 pointer-events-none" : "opacity-100"
      }`}
    >
      {/* Dynamic Animated Pulse Core */}
      <div className="relative flex items-center justify-center mb-8">
        {/* Outer Pulsing Ring */}
        <div className="w-28 h-28 rounded-full border-2 border-purple-500/20 animate-ping absolute" />
        <div className="w-20 h-20 rounded-full border border-purple-500/40 animate-pulse absolute" />

        {/* Center Geometric Traffic Signal Light Loader */}
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-[#634ca6] to-[#8c6bd6] shadow-2xl shadow-purple-600/40 flex items-center justify-center z-10 relative">
          <div className="flex gap-1.5 items-center">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-400 animate-bounce" style={{ animationDelay: "0ms" }} />
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-bounce" style={{ animationDelay: "150ms" }} />
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-bounce" style={{ animationDelay: "300ms" }} />
          </div>
        </div>
      </div>

      {/* Brand Title */}
      <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-white mb-2">
        CityFlow<span className="text-[#a78bfa]">X</span>
      </h1>

      {/* Dynamic Status Text */}
      <p className="text-xs font-semibold text-purple-200/80 mb-6 tracking-wide h-4">
        {statusText}
      </p>

      {/* Progress Bar Container */}
      <div className="w-64 max-w-full space-y-2">
        <div className="w-full h-1.5 bg-purple-950/80 rounded-full overflow-hidden p-0.5 border border-purple-800/40">
          <div
            className="h-full bg-gradient-to-r from-purple-500 to-indigo-400 rounded-full transition-all duration-75 ease-out shadow-sm"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="flex justify-between items-center text-[10px] font-bold text-purple-300/60 uppercase tracking-widest px-0.5">
          <span>Loading Matrix</span>
          <span>{progress}%</span>
        </div>
      </div>
    </div>
  );
}
