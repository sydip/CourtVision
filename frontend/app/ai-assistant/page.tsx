import { AppShell } from "@/components/app-shell";
import { DataAssistant } from "@/components/assistant/data-assistant";

export default function AiAssistantPage() {
  return (
    <AppShell active="Jordan" variant="topbar">
      <DataAssistant />
    </AppShell>
  );
}
