"use client";

import React from "react";
import LottieError from "@/components/ui/LottieError";

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#ebedee] p-6 text-slate-900 font-sans">
      <div className="max-w-md w-full">
        <LottieError 
          size="lg"
          title="Page Not Found or Failed to Load"
          text="The requested resource, traffic junction telemetry, or commuter dashboard route could not be located."
          showRetry={true}
          onRetry={() => {
            if (typeof window !== "undefined") window.location.href = "/";
          }}
          className="w-full shadow-md border border-slate-200/80 p-8"
        />
      </div>
    </div>
  );
}
