"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { SeasonProvider } from "@/lib/state/season-context";

type ProvidersProps = {
  children: React.ReactNode;
};

export function Providers({ children }: ProvidersProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
            retry: 1,
            // Keep fetched data "fresh" so switching tabs / revisiting a page serves it
            // from cache instantly instead of showing a spinner and re-fetching each time.
            staleTime: 60_000,
            gcTime: 5 * 60_000,
            refetchOnMount: false,
            refetchOnReconnect: false,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      <SeasonProvider>{children}</SeasonProvider>
    </QueryClientProvider>
  );
}
