import { FormEvent, useEffect, useState } from "react";

import { api, ApiError, setPasscode } from "../api";

interface Props {
  /** Called with true once a correct passcode is saved, false if cancelled. */
  onDone: (unlocked: boolean) => void;
}

/**
 * Asks for the shared passcode, checks it with the server, and remembers it
 * on this device if it's right.
 */
export default function PasscodeDialog({ onDone }: Props) {
  const [value, setValue] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Close on Escape.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onDone(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onDone]);

  async function unlock(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    try {
      await api.checkPasscode(value);
      setPasscode(value);
      onDone(true);
    } catch (e) {
      setProblem(
        e instanceof ApiError && e.status === 401
          ? "That passcode isn't right."
          : e instanceof Error
            ? e.message
            : String(e),
      );
      setBusy(false);
    }
  }

  return (
    <div className="overlay" onClick={() => onDone(false)}>
      <form
        className="dialog"
        role="dialog"
        aria-modal
        aria-label="Enter passcode"
        onClick={(e) => e.stopPropagation()}
        onSubmit={unlock}
      >
        <h2>Enter passcode</h2>
        <p className="muted">Anyone can look. Making changes needs the group's passcode.</p>

        <label className="field">
          <span>Passcode</span>
          <input
            autoFocus
            required
            type="password"
            autoComplete="current-password"
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              setProblem(null);
            }}
          />
        </label>
        {problem && (
          <p className="field-error" role="alert">
            {problem}
          </p>
        )}

        <div className="dialog-actions">
          <span className="spacer" />
          <button type="button" className="secondary-button" onClick={() => onDone(false)}>
            Cancel
          </button>
          <button type="submit" className="primary-button small" disabled={busy}>
            Unlock
          </button>
        </div>
      </form>
    </div>
  );
}
