import type { Metadata } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";

const plusJakartaSans = Plus_Jakarta_Sans({
  variable: "--font-google-sans",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "CityFlowX",
  description: "CityFlowX - Smart City Urban Traffic AI & Autonomous Flow Control",
  icons: {
    icon: "/cityflowx-logo.png",
    shortcut: "/cityflowx-logo.png",
    apple: "/cityflowx-logo.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${plusJakartaSans.variable} h-full antialiased font-sans`}
    >
      <body className="min-h-full flex flex-col font-sans bg-[#ebedee] text-slate-900">
        {children}
      </body>
    </html>
  );
}
