import { PlayerProfile } from "@/components/player-profile";

type PlayerProfilePageProps = {
  params: {
    playerId: string;
  };
};

export default function PlayerProfilePage({ params }: PlayerProfilePageProps) {
  return <PlayerProfile playerId={Number(params.playerId)} />;
}
