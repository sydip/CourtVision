import { Suspense } from "react";

import { CompareDashboard } from "@/components/compare-dashboard";

export default function ComparePage() {
  return (
    <Suspense fallback={null}>
      <CompareDashboard />
    </Suspense>
  );
}
