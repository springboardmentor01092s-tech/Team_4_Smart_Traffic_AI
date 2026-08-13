"use client";

import React from "react";
import LoginPage from "@/components/auth/LoginPage";
import ClickSpark from "@/components/ui/ClickSpark";

export default function Home() {
  return (
    <ClickSpark
      sparkColor="#18181b"
      sparkSize={12}
      sparkRadius={22}
      sparkCount={9}
      duration={400}
    >
      <LoginPage />
    </ClickSpark>
  );
}
