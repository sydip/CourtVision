import { Suspense } from "react";

import { RostersDashboard } from "@/components/rosters-dashboard";

export default function TeamsPage() {
  return (
    <Suspense fallback={null}>
      <RostersDashboard />
    </Suspense>
  );
}
