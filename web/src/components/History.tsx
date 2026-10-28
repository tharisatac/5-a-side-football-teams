import { Match, Team } from "../api";
import { matchDate, rating } from "../format";

/** Every match, newest first, with the winner highlighted. */
export default function History({ matches }: { matches: Match[] }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>History</h2>
        <span className="muted">{matches.length} matches</span>
      </div>
      {matches.length === 0 ? (
        <p className="muted">No matches yet. Pick some teams on Match day.</p>
      ) : (
        <ol className="history">
          {matches.map((match) => (
            <li key={match.id} className="history-item">
              <div className="history-head">
                <span className="history-id">#{match.id}</span>
                <span className="muted">{matchDate(match.created_at)}</span>
                <span className={match.winner ? "pill winner" : "pill"}>
                  {match.winner === "team1"
                    ? "Team 1 won"
                    : match.winner === "team2"
                      ? "Team 2 won"
                      : "Not played yet"}
                </span>
              </div>
              <div className="history-teams">
                <TeamLine team={match.team1} side="team1" won={match.winner === "team1"} />
                <span className="versus">vs</span>
                <TeamLine team={match.team2} side="team2" won={match.winner === "team2"} />
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function TeamLine({ team, side, won }: { team: Team; side: string; won: boolean }) {
  return (
    <div className={`team-line ${side}${won ? " won" : ""}`}>
      <span className="team-line-rating">{rating(team.rating)}</span>
      <span>{team.players.map((p) => p.name).join(", ")}</span>
    </div>
  );
}
