"use client";

import React, { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';

const DotLottieReact = dynamic(
  () => import('@lottiefiles/dotlottie-react').then((mod) => mod.DotLottieReact),
  { ssr: false }
);

interface LottieLoaderProps {
  text?: string;
  className?: string;
  size?: "sm" | "md" | "lg" | "xl";
}

export default function LottieLoader({ 
  text = "Loading smart traffic insights...", 
  className = "",
  size = "md" 
}: LottieLoaderProps) {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  const sizeClasses = {
    sm: "w-20 h-20",
    md: "w-32 h-32",
    lg: "w-48 h-48",
    xl: "w-64 h-64"
  };

  return (
    <div className={`flex flex-col items-center justify-center p-4 text-center select-none ${className}`}>
      <div className={`${sizeClasses[size]} relative flex items-center justify-center pointer-events-none`}>
        {mounted && (
          <DotLottieReact
            src="https://lottie.host/1c61404c-6a62-4738-aa94-3ddd979b18b2/N16RyJF5PP.lottie"
            loop
            autoplay
            style={{ width: '100%', height: '100%' }}
          />
        )}
      </div>
      {text && (
        <p className="mt-2 text-xs font-extrabold tracking-wide text-slate-500 animate-pulse">
          {text}
        </p>
      )}
    </div>
  );
}
