import { Suspense } from "react";

import { RostersDashboard } from "@/components/rosters-dashboard";

export default async function TeamPage({ params }: { params: Promise<{ teamId: string }> }) {
  const { teamId } = await params;
  return (
    <Suspense fallback={null}>
      <RostersDashboard initialTeamId={Number(teamId)} />
    </Suspense>
  );
}
