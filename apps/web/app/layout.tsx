import "./globals.css";
import type { ReactNode } from "react";

export const metadata = {
  title: "Phoenix Investigation Panel V2",
  description: "Phoenix Investigation Panel V2",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ro">
      <body>
        <div className="app-shell">
          <aside className="sidebar">
            <div className="brand">PHX V2</div>
            <nav>
              <a href="/">Dashboard</a>
              <a href="/imports">Imports</a>
              <a href="/events">Events Explorer</a>
              <a href="/players">Players</a>
              <a href="/containers">Containers</a>
              <a href="/report-packs">Report Packs</a>
            </nav>
          </aside>
          <main className="content">{children}</main>
        </div>
      </body>
    </html>
  );
}
