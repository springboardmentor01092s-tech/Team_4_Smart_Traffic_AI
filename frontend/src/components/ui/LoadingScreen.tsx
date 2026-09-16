"use client";

import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";

const DotLottieReact = dynamic(
  () => import("@lottiefiles/dotlottie-react").then((mod) => mod.DotLottieReact),
  { ssr: false }
);

interface LoadingScreenProps {
  onComplete?: () => void;
  durationMs?: number;
  customStatus?: string;
}

export default function LoadingScreen({ onComplete, durationMs = 1800, customStatus }: LoadingScreenProps) {
  const [progress, setProgress] = useState(0);
  const [statusText, setStatusText] = useState(customStatus || "Initializing CityFlowX AI...");
  const [isFadingOut, setIsFadingOut] = useState(false);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    const startTime = Date.now();

    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const pct = Math.min(100, Math.floor((elapsed / durationMs) * 100));
      setProgress(pct);

      if (!customStatus) {
        if (pct < 35) {
          setStatusText("Initializing CityFlowX AI Engine...");
        } else if (pct < 70) {
          setStatusText("Connecting to Supabase PostgreSQL Telemetry...");
        } else if (pct < 95) {
          setStatusText("Synchronizing Urban Signal Matrix...");
        } else {
          setStatusText("System Ready");
        }
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
  }, [durationMs, onComplete, customStatus]);

  return (
    <div
      className={`fixed inset-0 z-50 bg-[#121118] text-white flex flex-col items-center justify-center p-6 select-none transition-opacity duration-500 ease-out ${
        isFadingOut ? "opacity-0 pointer-events-none" : "opacity-100"
      }`}
    >
      {/* 300px by 300px Full Page Reload & Redirect Lottie Animation */}
      <div className="relative flex items-center justify-center mb-2" style={{ width: "300px", height: "300px", maxWidth: "100%" }}>
        {mounted && (
          <DotLottieReact
            src="https://lottie.host/4e5fb1ae-609c-47f1-98cb-0e9899f9e4de/AG3fq01L8q.lottie"
            loop
            autoplay
            style={{ width: "300px", height: "300px", maxWidth: "100%" }}
          />
        )}
      </div>

      {/* Brand Title */}
      <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-white mb-2">
        CityFlow<span className="text-[#a78bfa]">X</span>
      </h1>

      {/* Dynamic Status Text */}
      <p className="text-xs font-semibold text-purple-200/80 mb-6 tracking-wide h-4">
        {statusText}
      </p>
    </div>
  );
}
