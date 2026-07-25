import { AssistantDashboard } from "@/components/assistant-dashboard";
import { AppShell } from "@/components/app-shell";

export default function AssistantPage() {
  return (
    <AppShell active="Jordan" variant="topbar">
      <AssistantDashboard />
    </AppShell>
  );
}
