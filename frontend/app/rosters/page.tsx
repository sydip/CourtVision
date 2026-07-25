import { Suspense } from "react";

import { RostersDashboard } from "@/components/rosters-dashboard";

export default function RostersPage() {
  return (
    <Suspense fallback={null}>
      <RostersDashboard />
    </Suspense>
  );
}
