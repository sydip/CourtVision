"use client";

import { AppShell } from "@/components/app-shell";

type ComingSoonPageProps = {
  section: "Playoffs" | "Draft" | "Offseason";
  title: string;
  blurb: string;
};

export function ComingSoonPage({ blurb, section, title }: ComingSoonPageProps) {
  return (
    <AppShell active={section} variant="topbar">
      <div className="section-coming-soon">
        <div className="panel section-coming-soon-card">
          <span className="section-coming-soon-eyebrow">{section}</span>
          <h1>{title}</h1>
          <p>{blurb}</p>
        </div>
      </div>
    </AppShell>
  );
}
