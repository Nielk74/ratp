"use client";

import Link from "next/link";

export function Header() {
  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <Link href="/" className="flex items-center space-x-3">
            <div className="text-2xl">🚇</div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                RATP Live Tracker
              </h1>
              <p className="text-xs text-gray-500">Real-time Paris Transit</p>
            </div>
          </Link>

          <nav className="hidden md:flex items-center space-x-6">
            <Link
              href="/"
              className="text-gray-700 hover:text-primary transition"
            >
              Dashboard
            </Link>
            <Link
              href="/map"
              className="text-gray-700 hover:text-primary transition"
            >
              Map
            </Link>
            <Link
              href="/webhooks"
              className="text-gray-700 hover:text-primary transition"
            >
              Alerts
            </Link>
            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-700 hover:text-primary transition"
            >
              API Docs
            </a>
          </nav>

          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 bg-success rounded-full animate-pulse"></div>
            <span className="text-sm text-gray-600">Live</span>
          </div>
        </div>
      </div>
    </header>
  );
}
