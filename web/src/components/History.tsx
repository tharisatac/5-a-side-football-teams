import { useState } from "react";

import { api, Match, Team, TeamKey } from "../api";
import type { Run } from "../App";
import { matchLabel, rating } from "../format";

const RESULTS: { winner: TeamKey | null; label: string }[] = [
  { winner: "team1", label: "Team 1 won" },
  { winner: "team2", label: "Team 2 won" },
  { winner: null, label: "Not played" },
];

/**
 * Every match, newest first, with the winner highlighted. Each result can be
 * changed or cleared, and any match deleted; form changes are undone to match.
 */
export default function History({ matches, run }: { matches: Match[]; run: Run }) {
  const [busy, setBusy] = useState(false);

  async function act(action: () => Promise<unknown>) {
    setBusy(true);
    await run(action);
    setBusy(false);
  }

  function setResult(match: Match, winner: TeamKey | null) {
    if (winner === match.winner) return;
    act(() =>
      winner ? api.recordResult(match.id, winner) : api.clearResult(match.id),
    );
  }

  function remove(match: Match) {
    const undo = match.winner ? " Its form changes will be undone." : "";
    if (window.confirm(`Delete the match from ${matchLabel(match, matches)}?${undo}`)) {
      act(() => api.deleteMatch(match.id));
    }
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>History</h2>
        <span className="muted">
          {matches.length} {matches.length === 1 ? "match" : "matches"}
        </span>
      </div>
      {matches.length === 0 ? (
        <p className="muted">No matches yet. Pick some teams on Match day.</p>
      ) : (
        <ol className="history">
          {matches.map((match) => (
            <li key={match.id} className="history-item">
              <div className="history-head">
                <span className="history-date">{matchLabel(match, matches)}</span>
              </div>
              <div className="history-teams">
                <TeamLine team={match.team1} side="team1" won={match.winner === "team1"} />
                <span className="versus">vs</span>
                <TeamLine team={match.team2} side="team2" won={match.winner === "team2"} />
              </div>
              <div className="history-actions">
                <div className="segmented" role="group" aria-label={`Result of the match from ${matchLabel(match, matches)}`}>
                  {RESULTS.map(({ winner, label }) => (
                    <button
                      key={label}
                      className={match.winner === winner ? "active" : undefined}
                      aria-pressed={match.winner === winner}
                      disabled={busy}
                      onClick={() => setResult(match, winner)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
                <button
                  className="link-button danger"
                  disabled={busy}
                  onClick={() => remove(match)}
                >
                  Delete
                </button>
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
