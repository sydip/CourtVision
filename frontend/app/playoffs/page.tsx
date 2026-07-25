import { Suspense } from "react";

import { PlayoffsBracket } from "@/components/playoffs-bracket";

export default function PlayoffsPage() {
  return (
    <Suspense fallback={null}>
      <PlayoffsBracket />
    </Suspense>
  );
}
