import { useState } from "react";

import { Player, SKILLS } from "../api";
import type { Run } from "../App";
import { formTrend, rating } from "../format";
import PlayerEditor from "./PlayerEditor";

const SHORT: Record<string, string> = {
  shooting: "SHO",
  dribbling: "DRI",
  passing: "PAS",
  tackling: "TAC",
  fitness: "FIT",
  goalkeeping: "GK",
};

const TREND_ARROW = { up: "▲", down: "▼", flat: "■" };

/** Everyone in the squad, best first. Click a card to edit that player. */
export default function Squad({ players, run }: { players: Player[]; run: Run }) {
  // The player being edited, "new" when adding one, or null when closed.
  const [editing, setEditing] = useState<Player | "new" | null>(null);
  const ranked = [...players].sort((a, b) => b.rating - a.rating);

  return (
    <>
      <section className="panel">
        <div className="panel-head">
          <h2>Squad</h2>
          <button className="primary-button small" onClick={() => setEditing("new")}>
            + Add player
          </button>
        </div>
        {players.length === 0 ? (
          <p className="muted">No players yet. Add the first one.</p>
        ) : (
          <div className="cards">
            {ranked.map((player) => (
              <PlayerCard
                key={player.name}
                player={player}
                onClick={() => setEditing(player)}
              />
            ))}
          </div>
        )}
      </section>
      {editing && (
        <PlayerEditor
          player={editing === "new" ? undefined : editing}
          run={run}
          onClose={() => setEditing(null)}
        />
      )}
    </>
  );
}

function PlayerCard({ player, onClick }: { player: Player; onClick: () => void }) {
  const trend = formTrend(player.form);
  return (
    <button className="card" onClick={onClick}>
      <div className="card-top">
        <span className="card-rating">{rating(player.rating)}</span>
        <span className="card-name">{player.name}</span>
      </div>
      <div className={`card-form ${trend}`}>
        {TREND_ARROW[trend]} Form {player.form}
      </div>
      <ul className="skill-bars">
        {SKILLS.map((skill) => (
          <li key={skill}>
            <span className="skill-label">{SHORT[skill]}</span>
            <span className="skill-track">
              <span
                className="skill-fill"
                style={{ width: `${player.skills[skill] * 10}%` }}
              />
            </span>
            <span className="skill-value">{player.skills[skill]}</span>
          </li>
        ))}
      </ul>
    </button>
  );
}
