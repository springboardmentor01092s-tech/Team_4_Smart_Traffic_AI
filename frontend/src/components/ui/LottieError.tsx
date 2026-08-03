"use client";

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import { RefreshCw, AlertTriangle } from 'lucide-react';

const DotLottieReact = dynamic(
  () => import('@lottiefiles/dotlottie-react').then((mod) => mod.DotLottieReact),
  { ssr: false }
);

interface LottieErrorProps {
  title?: string;
  text?: string;
  className?: string;
  size?: "sm" | "md" | "lg" | "xl";
  onRetry?: () => void;
  showRetry?: boolean;
}

export default function LottieError({ 
  title = "System Notice or Failure to Load",
  text = "An unexpected error occurred while communicating with the telemetry server or loading this module.", 
  className = "",
  size = "md",
  onRetry,
  showRetry = false
}: LottieErrorProps) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const sizeClasses = {
    sm: "w-20 h-20",
    md: "w-32 h-32",
    lg: "w-48 h-48",
    xl: "w-64 h-64"
  };

  const handleRetry = () => {
    if (onRetry) {
      onRetry();
    } else if (typeof window !== "undefined") {
      window.location.reload();
    }
  };

  return (
    <div className={`flex flex-col items-center justify-center p-6 text-center bg-white border border-slate-200 rounded-3xl shadow-sm max-w-md mx-auto my-4 select-none ${className}`}>
      <div className={`${sizeClasses[size]} relative flex items-center justify-center pointer-events-none mb-3`}>
        {mounted && (
          <DotLottieReact
            src="https://lottie.host/32e0e466-4e01-4943-9cff-4e77a1ecb68f/Sg4vJnoW1E.lottie"
            loop
            autoplay
            style={{ width: '100%', height: '100%' }}
          />
        )}
      </div>
      
      {title && (
        <h4 className="text-base font-extrabold text-slate-800 tracking-tight flex items-center gap-2 justify-center mb-1">
          <AlertTriangle className="w-4 h-4 text-rose-500 shrink-0" />
          <span>{title}</span>
        </h4>
      )}

      {text && (
        <p className="text-xs font-medium text-slate-500 max-w-xs mb-4">
          {text}
        </p>
      )}

      {(showRetry || onRetry) && (
        <button
          onClick={handleRetry}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-extrabold tracking-wide text-white bg-[#121118] hover:bg-slate-800 rounded-xl shadow transition duration-200 active:scale-95"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry / Refresh</span>
        </button>
      )}
    </div>
  );
}
