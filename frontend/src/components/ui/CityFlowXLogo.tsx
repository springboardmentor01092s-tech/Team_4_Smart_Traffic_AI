"use client";

import React from "react";
import Image from "next/image";

interface LogoProps {
  className?: string;
  size?: "sm" | "md" | "lg" | "xl";
  lightMode?: boolean;
}

export default function CityFlowXLogo({ className = "", size = "md", lightMode = true }: LogoProps) {
  const pixelSizes = {
    sm: { width: 100, height: 50 },
    md: { width: 140, height: 70 },
    lg: { width: 200, height: 100 },
    xl: { width: 280, height: 140 },
  }[size];

  return (
    <div className={`inline-flex items-center justify-center select-none ${className}`}>
      <Image
        src="/cityflowx-logo.png"
        alt="CityFlowX Official Logo"
        width={pixelSizes.width}
        height={pixelSizes.height}
        priority
        className={`object-contain transition-all ${
          !lightMode ? "invert brightness-200" : "drop-shadow-sm"
        }`}
      />
    </div>
  );
}
