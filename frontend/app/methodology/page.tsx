import { AppShell } from "@/components/app-shell";
import { MethodologyPage } from "@/components/methodology/methodology-page";

export default function MethodologyRoute() {
  return (
    <AppShell active="Methodology">
      <MethodologyPage />
    </AppShell>
  );
}
