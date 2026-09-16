"use client";

import React, { useEffect } from "react";
import { CheckCircle2, AlertCircle, ShieldAlert } from "lucide-react";

export interface ToastAlertProps {
  type: "success" | "error" | "warning";
  message: string;
  onClose?: () => void;
  autoDismissMs?: number;
}

export default function ToastAlert({ type, message, onClose, autoDismissMs = 3000 }: ToastAlertProps) {
  useEffect(() => {
    if (onClose) {
      const timer = setTimeout(() => {
        onClose();
      }, autoDismissMs);
      return () => clearTimeout(timer);
    }
  }, [onClose, autoDismissMs]);

  const styles = {
    error: "bg-rose-50 border-rose-200 text-rose-800 shadow-rose-500/10",
    success: "bg-emerald-50 border-emerald-200 text-emerald-800 shadow-emerald-500/10",
    warning: "bg-amber-500 text-slate-950 shadow-amber-500/10"
  };

  return (
    <div className="fixed top-6 right-6 z-50 animate-bounce duration-300 transition-all">
      <div className={`flex items-center gap-3 px-5 py-3.5 rounded-2xl shadow-2xl border text-xs font-bold backdrop-blur-md ${styles[type]}`}>
        {type === "error" && <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />}
        {type === "success" && <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />}
        {type === "warning" && <ShieldAlert className="w-5 h-5 shrink-0" />}
        <span>{message}</span>
      </div>
    </div>
  );
}
