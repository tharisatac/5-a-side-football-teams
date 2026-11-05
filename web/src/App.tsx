import { useCallback, useEffect, useState } from "react";

import { api, ApiError, getPasscode, Match, Player, setPasscode } from "./api";
import History from "./components/History";
import MatchDay from "./components/MatchDay";
import PasscodeDialog from "./components/PasscodeDialog";
import Squad from "./components/Squad";

type Tab = "match" | "squad" | "history";

/** The tab named in the URL (e.g. #squad), so a refresh stays on it. */
function tabFromUrl(): Tab {
  const hash = window.location.hash.slice(1);
  return hash === "squad" || hash === "history" ? hash : "match";
}

const TABS: { id: Tab; label: string }[] = [
  { id: "match", label: "Match day" },
  { id: "squad", label: "Squad" },
  { id: "history", label: "History" },
];

/**
 * Runs an API action, then reloads the data. Returns whether the action
 * succeeded; on failure the error is shown in a toast. If the action needs
 * the passcode, asks for it and tries again. A failed reload after
 * a successful action still counts as success, so the user isn't tempted to
 * repeat it (e.g. creating a second match).
 */
export type Run = (action: () => Promise<unknown>) => Promise<boolean>;

function message(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export default function App() {
  const [tab, setTab] = useState<Tab>(tabFromUrl);
  const [players, setPlayers] = useState<Player[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unlocked, setUnlocked] = useState(() => getPasscode() !== null);
  // While the passcode dialog is open: how to report back whether it was
  // unlocked, to whoever opened it.
  const [onPasscode, setOnPasscode] = useState<((unlocked: boolean) => void) | null>(null);

  const refresh = useCallback(async () => {
    const [newPlayers, newMatches] = await Promise.all([
      api.listPlayers(),
      api.listMatches(),
    ]);
    setPlayers(newPlayers);
    setMatches(newMatches);
  }, []);

  /** Locks or unlocks this device, then reloads to show or hide ratings. */
  const changeLock = useCallback(
    (nowUnlocked: boolean) => {
      if (!nowUnlocked) setPasscode(null);
      setUnlocked(nowUnlocked);
      refresh().catch((e) => setError(message(e)));
    },
    [refresh],
  );

  /** Opens the passcode dialog; resolves true once it's unlocked. */
  const askForPasscode = useCallback(
    () =>
      new Promise<boolean>((resolve) => {
        // A function in state must be wrapped, or React would call it.
        setOnPasscode(() => (ok: boolean) => {
          setOnPasscode(null);
          if (ok) changeLock(true);
          resolve(ok);
        });
      }),
    [changeLock],
  );

  const run: Run = useCallback(
    async (action) => {
      for (;;) {
        try {
          await action();
          break;
        } catch (e) {
          if (!(e instanceof ApiError && e.status === 401)) {
            setError(message(e));
            return false;
          }
          // No passcode, or a remembered one that has since changed.
          changeLock(false);
          if (!(await askForPasscode())) return false;
        }
      }
      try {
        await refresh();
      } catch (e) {
        setError(`Saved, but couldn't reload: ${message(e)}`);
      }
      return true;
    },
    [refresh, askForPasscode, changeLock],
  );

  useEffect(() => {
    refresh()
      .catch((e) => setError(message(e)))
      .finally(() => setLoaded(true));
  }, [refresh]);

  // A remembered passcode may have been changed since; if so, forget it so
  // the badge doesn't claim "Editing".
  useEffect(() => {
    const remembered = getPasscode();
    if (remembered === null) return;
    api.checkPasscode(remembered).catch((e) => {
      if (e instanceof ApiError && e.status === 401) changeLock(false);
    });
  }, [changeLock]);

  // Hide the error toast after a few seconds.
  useEffect(() => {
    if (!error) return;
    const timer = setTimeout(() => setError(null), 5000);
    return () => clearTimeout(timer);
  }, [error]);

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <span className="brand-ball" aria-hidden>
            ⚽
          </span>
          <span>
            5-a-side <em>team decider</em>
          </span>
          <button
            className="lock-button"
            title={unlocked ? "Lock changes on this device" : "Enter the passcode to make changes"}
            onClick={() => (unlocked ? changeLock(false) : void askForPasscode())}
          >
            {unlocked ? "🔓 Editing" : "🔒 View only"}
          </button>
        </div>
        <nav className="tabs" aria-label="Sections">
          {TABS.map(({ id, label }) => (
            <button
              key={id}
              className={tab === id ? "tab active" : "tab"}
              aria-current={tab === id ? "page" : undefined}
              onClick={() => {
                setTab(id);
                window.location.hash = id;
              }}
            >
              {label}
            </button>
          ))}
        </nav>
      </header>

      <main className="content">
        {!loaded ? (
          <p className="muted center">Loading…</p>
        ) : tab === "match" ? (
          <MatchDay players={players} matches={matches} run={run} />
        ) : tab === "squad" ? (
          <Squad players={players} run={run} unlock={() => void askForPasscode()} />
        ) : (
          <History matches={matches} run={run} />
        )}
      </main>

      {onPasscode && <PasscodeDialog onDone={onPasscode} />}

      {error && (
        <div className="toast" role="alert" onClick={() => setError(null)}>
          {error}
        </div>
      )}
    </div>
  );
}
