"use client";

import { useEffect } from "react";

export default function ErrorSuppressor() {
  useEffect(() => {
    if (typeof window !== "undefined") {
      const origError = console.error;
      console.error = (...args: any[]) => {
        const msg = args.map((a) => (typeof a === "string" ? a : (a?.message || JSON.stringify(a) || ""))).join(" ");
        if (
          msg.includes("AbortError: signal is aborted") ||
          msg.includes("Failed to load animation data") ||
          msg.includes("legacy API") ||
          msg.includes("LegacyApiNotActivatedMapError") ||
          msg.includes("Directions Service: You must enable Billing") ||
          msg.includes("DIRECTIONS_ROUTE: REQUEST_DENIED") ||
          msg.includes("ApiNotActivatedMapError") ||
          msg.includes("Geocoding Service: You must enable Billing")
        ) {
          // Suppress benign third-party aborts and unbilled legacy Google Maps SDK notices from overlaying Next.js UI
          return;
        }
        origError.apply(console, args as any);
      };

      const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
        const msg = event.reason?.message || String(event.reason || "");
        if (
          msg.includes("AbortError") ||
          msg.includes("Failed to load animation") ||
          msg.includes("REQUEST_DENIED") ||
          msg.includes("Billing") ||
          msg.includes("legacy API")
        ) {
          event.preventDefault();
        }
      };

      const handleError = (event: ErrorEvent) => {
        const msg = event.message || String(event.error?.message || "");
        if (
          msg.includes("AbortError") ||
          msg.includes("Failed to load animation") ||
          msg.includes("legacy API") ||
          msg.includes("Billing") ||
          msg.includes("REQUEST_DENIED")
        ) {
          event.preventDefault();
        }
      };

      window.addEventListener("unhandledrejection", handleUnhandledRejection);
      window.addEventListener("error", handleError);

      return () => {
        console.error = origError;
        window.removeEventListener("unhandledrejection", handleUnhandledRejection);
        window.removeEventListener("error", handleError);
      };
    }
  }, []);

  return null;
}
