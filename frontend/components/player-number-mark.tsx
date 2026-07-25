import type { PlayerListItem, Team } from "@/lib/api/schemas";

type PlayerNumberMarkProps = {
  player: Pick<PlayerListItem, "full_name" | "jersey_number"> &
    Partial<Pick<PlayerListItem, "nba_player_id">> & {
      team?: Team | null;
    };
  className?: string;
};

const jerseyNumberOverridesByPlayerId: Record<number, string> = {
  1626164: "1",
};

export function PlayerNumberMark({ className, player }: PlayerNumberMarkProps) {
  const jerseyNumber =
    (player.nba_player_id ? jerseyNumberOverridesByPlayerId[player.nba_player_id] : undefined) ??
    player.jersey_number?.trim() ??
    "--";
  const accessibleLabel = `${player.full_name} glowing jersey number ${jerseyNumber}`;

  return (
    <svg
      aria-label={accessibleLabel}
      className={["player-number-mark", className].filter(Boolean).join(" ")}
      role="img"
      viewBox="0 0 100 100"
    >
      <text className="number-mark-text" textAnchor="middle" x="50" y="64">
        {jerseyNumber}
      </text>
    </svg>
  );
}
