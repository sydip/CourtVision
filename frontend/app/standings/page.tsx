import { Suspense } from "react";

import { StandingsDashboard } from "@/components/standings-dashboard";

export default function StandingsPage() {
  return (
    <Suspense fallback={null}>
      <StandingsDashboard />
    </Suspense>
  );
}
