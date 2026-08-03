"use client";

import React, { useEffect } from "react";
import LottieError from "@/components/ui/LottieError";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log error cleanly without crashing UI
    console.warn("Caught by Next.js App Router Error Boundary:", error);
  }, [error]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#ebedee] p-6 text-slate-900 font-sans">
      <div className="max-w-md w-full">
        <LottieError 
          size="xl"
          title="Application Encountered an Issue"
          text="An internal telemetry or rendering error occurred. Our automated error recovery mechanism has caught this event."
          showRetry={true}
          onRetry={() => reset()}
          className="w-full shadow-md border border-slate-200/80 p-8"
        />
      </div>
    </div>
  );
}
