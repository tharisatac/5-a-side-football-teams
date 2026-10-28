import { useState } from "react";

import { api, Match, Player, TeamKey } from "../api";
import type { Run } from "../App";
import { initials, matchDate, rating } from "../format";
import Pitch, { BalanceBar } from "./Pitch";

interface Props {
  players: Player[];
  matches: Match[];
  run: Run;
}

/**
 * Pick who's playing, balance them into teams, then record who won. Shows
 * the open match if there is one, otherwise the player picker.
 */
export default function MatchDay({ players, matches, run }: Props) {
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);

  const latest: Match | undefined = matches[0];
  const byName = [...players].sort((a, b) => a.name.localeCompare(b.name));
  const open = latest?.winner === null ? latest : undefined;

  async function act(action: () => Promise<unknown>) {
    setBusy(true);
    const ok = await run(action);
    setBusy(false);
    return ok;
  }

  function toggle(name: string) {
    const next = new Set(selected);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    setSelected(next);
  }

  if (open) {
    const names = [...open.team1.players, ...open.team2.players].map((p) => p.name);
    return (
      <section className="panel">
        <div className="panel-head">
          <h2>Match #{open.id}</h2>
          <span className="muted">{matchDate(open.created_at)}</span>
        </div>
        <BalanceBar team1={open.team1} team2={open.team2} />
        <Pitch match={open} />
        <p className="prompt">Who won?</p>
        <div className="result-buttons">
          {(["team1", "team2"] as TeamKey[]).map((key) => (
            <button
              key={key}
              className={`result-button ${key}`}
              disabled={busy}
              onClick={() => act(() => api.recordResult(open.id, key))}
            >
              {key === "team1" ? "Team 1" : "Team 2"} won
            </button>
          ))}
        </div>
        <button
          className="link-button"
          disabled={busy}
          onClick={async () => {
            if (await act(() => api.cancelMatch(open.id))) setSelected(new Set(names));
          }}
        >
          Cancel this match
        </button>
      </section>
    );
  }

  return (
    <>
      {latest && <LastResult match={latest} />}
      <section className="panel">
        <div className="panel-head">
          <h2>Who's playing?</h2>
          <span className="muted">{selected.size} selected</span>
        </div>
        {players.length === 0 ? (
          <p className="muted">Add some players in the Squad tab first.</p>
        ) : (
          <>
            <div className="chip-actions">
              <button
                className="link-button"
                onClick={() => setSelected(new Set(players.map((p) => p.name)))}
              >
                Select all
              </button>
              <button className="link-button" onClick={() => setSelected(new Set())}>
                Clear
              </button>
            </div>
            <div className="chips">
              {byName.map((player) => (
                <button
                  key={player.name}
                  className={selected.has(player.name) ? "chip selected" : "chip"}
                  aria-pressed={selected.has(player.name)}
                  onClick={() => toggle(player.name)}
                >
                  <span className="chip-badge">{initials(player.name)}</span>
                  <span className="chip-name">{player.name}</span>
                  <span className="chip-rating">{rating(player.rating)}</span>
                </button>
              ))}
            </div>
            <button
              className="primary-button"
              disabled={selected.size < 2 || busy}
              onClick={() => act(() => api.createMatch([...selected]))}
            >
              Pick teams
            </button>
          </>
        )}
      </section>
    </>
  );
}

/** A compact summary of the last recorded match and its form changes. */
function LastResult({ match }: { match: Match }) {
  if (!match.winner) return null;
  const loser: TeamKey = match.winner === "team1" ? "team2" : "team1";

  return (
    <section className="panel last-result">
      <div className="panel-head">
        <h3>
          Last match · {match.winner === "team1" ? "Team 1" : "Team 2"} won
        </h3>
        <span className="muted">
          #{match.id} · {matchDate(match.created_at)}
        </span>
      </div>
      <div className="form-changes">
        {match[match.winner].players.map((p) => (
          <span key={p.name} className="form-change up">
            ▲ {p.name}
          </span>
        ))}
        {match[loser].players.map((p) => (
          <span key={p.name} className="form-change down">
            ▼ {p.name}
          </span>
        ))}
      </div>
    </section>
  );
}
