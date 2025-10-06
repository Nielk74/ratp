import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RATP Live Tracker",
  description: "Real-time monitoring for Paris public transport",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased bg-gray-50">
        {children}
      </body>
    </html>
  );
}
