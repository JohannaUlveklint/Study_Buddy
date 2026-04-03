import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";


export const metadata: Metadata = {
  title: "Study Buddy",
  description: "Phase 1 start flow for Study Buddy",
};


export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}