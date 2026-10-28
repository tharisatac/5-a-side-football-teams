import { Match, Team, TeamKey } from "../api";
import { initials, rating } from "../format";

const LABELS: Record<TeamKey, string> = { team1: "Team 1", team2: "Team 2" };

interface PitchProps {
  match: Match;
  /** The name of the player tapped first when swapping, if any. */
  picked?: string | null;
  /** Called when a player is tapped. Without it the players aren't tappable. */
  onPick?: (name: string, side: TeamKey) => void;
}

/** The two teams drawn on a football pitch, one per half. */
export default function Pitch({ match, picked, onPick }: PitchProps) {
  return (
    <div className="pitch">
      <div className="pitch-markings" aria-hidden />
      {(["team1", "team2"] as const).map((key) => (
        <TeamHalf
          key={key}
          side={key}
          team={match[key]}
          won={match.winner === key}
          picked={picked}
          onPick={onPick}
        />
      ))}
    </div>
  );
}

interface TeamHalfProps {
  side: TeamKey;
  team: Team;
  won: boolean;
  picked?: string | null;
  onPick?: (name: string, side: TeamKey) => void;
}

function TeamHalf({ side, team, won, picked, onPick }: TeamHalfProps) {
  return (
    <div className={`half ${side}`}>
      <div className="half-label">
        {LABELS[side]}
        {team.bonus > 1 && <span className="pill">×{team.bonus} boost</span>}
        {won && <span className="pill winner">Won</span>}
      </div>
      <ul className="tokens">
        {team.players.map((player) => {
          const content = (
            <>
              <span className="token-badge">{initials(player.name)}</span>
              <span className="token-name">{player.name}</span>
              <span className="token-rating">{rating(player.rating)}</span>
            </>
          );
          return (
            <li key={player.name}>
              {onPick ? (
                <button
                  className={picked === player.name ? "token picked" : "token"}
                  aria-pressed={picked === player.name}
                  onClick={() => onPick(player.name, side)}
                >
                  {content}
                </button>
              ) : (
                <span className="token">{content}</span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** How evenly matched the teams are, as a tug-of-war bar. */
export function BalanceBar({ team1, team2 }: { team1: Team; team2: Team }) {
  const total = team1.rating + team2.rating;
  const share = total > 0 ? (team1.rating / total) * 100 : 50;
  const gap = Math.abs(team1.rating - team2.rating);

  return (
    <div className="balance">
      <div className="balance-scores">
        <span className="score team1">{rating(team1.rating)}</span>
        <span className="balance-gap">
          {gap < 0.05 ? "Perfectly balanced" : `${rating(gap)} apart`}
        </span>
        <span className="score team2">{rating(team2.rating)}</span>
      </div>
      <div className="balance-bar">
        <div className="balance-fill" style={{ width: `${share}%` }} />
      </div>
    </div>
  );
}
