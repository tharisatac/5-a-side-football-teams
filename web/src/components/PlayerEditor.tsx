import { FormEvent, useEffect, useState } from "react";

import { api, Player, PlayerChanges, Skills, SKILLS } from "../api";
import type { Run } from "../App";

const DEFAULT_SKILLS = Object.fromEntries(SKILLS.map((s) => [s, 5])) as Skills;

interface Props {
  /** The player to edit, or undefined to add a new one. */
  player?: Player;
  run: Run;
  onClose: () => void;
}

/** A dialog to add a player, or change or remove an existing one. */
export default function PlayerEditor({ player, run, onClose }: Props) {
  const [name, setName] = useState(player?.name ?? "");
  const [skills, setSkills] = useState<Skills>(player?.skills ?? DEFAULT_SKILLS);
  const [form, setForm] = useState(player?.form ?? 5);
  const [busy, setBusy] = useState(false);

  // Close on Escape.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function save(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    const ok = await run(() =>
      player ? api.updatePlayer(player.name, changes(player, skills, form)) : api.addPlayer(name.trim(), skills),
    );
    setBusy(false);
    if (ok) onClose();
  }

  async function remove() {
    if (!player || !window.confirm(`Remove ${player.name}?`)) return;
    setBusy(true);
    const ok = await run(() => api.removePlayer(player.name));
    setBusy(false);
    if (ok) onClose();
  }

  return (
    <div className="overlay" onClick={onClose}>
      <form
        className="dialog"
        role="dialog"
        aria-modal
        aria-label={player ? `Edit ${player.name}` : "Add player"}
        onClick={(e) => e.stopPropagation()}
        onSubmit={save}
      >
        <h2>{player ? player.name : "New player"}</h2>

        {!player && (
          <label className="field">
            <span>Name</span>
            <input
              autoFocus
              required
              maxLength={50}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
        )}

        {SKILLS.map((skill) => (
          <Slider
            key={skill}
            label={skill}
            min={1}
            value={skills[skill]}
            onChange={(value) => setSkills({ ...skills, [skill]: value })}
          />
        ))}
        {player && <Slider label="form" min={0} value={form} onChange={setForm} />}

        <div className="dialog-actions">
          {player && (
            <button type="button" className="danger-button" disabled={busy} onClick={remove}>
              Remove
            </button>
          )}
          <span className="spacer" />
          <button type="button" className="secondary-button" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="primary-button small" disabled={busy}>
            {player ? "Save" : "Add"}
          </button>
        </div>
      </form>
    </div>
  );
}

function Slider(props: {
  label: string;
  min: number;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="slider">
      <span className="slider-label">{props.label}</span>
      <input
        type="range"
        min={props.min}
        max={10}
        step={1}
        value={props.value}
        onChange={(e) => props.onChange(Number(e.target.value))}
      />
      <span className="slider-value">{props.value}</span>
    </label>
  );
}

/**
 * Only the fields that changed, so untouched values (e.g. a 7.5 imported from
 * CSV) aren't rounded by the 1-step slider and rewritten.
 */
function changes(player: Player, skills: Skills, form: number): PlayerChanges {
  const result: PlayerChanges = {};
  for (const skill of SKILLS) {
    if (skills[skill] !== player.skills[skill]) result[skill] = skills[skill];
  }
  if (form !== player.form) result.form = form;
  return result;
}
