import { useCallback, useEffect, useState } from "react";

import { api, Match, Player } from "./api";
import History from "./components/History";
import MatchDay from "./components/MatchDay";
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
 * Runs an API action, then reloads the data. Returns whether it succeeded;
 * on failure the error is shown in a toast.
 */
export type Run = (action: () => Promise<unknown>) => Promise<boolean>;

export default function App() {
  const [tab, setTab] = useState<Tab>(tabFromUrl);
  const [players, setPlayers] = useState<Player[]>([]);
  const [matches, setMatches] = useState<Match[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const [newPlayers, newMatches] = await Promise.all([
      api.listPlayers(),
      api.listMatches(),
    ]);
    setPlayers(newPlayers);
    setMatches(newMatches);
  }, []);

  const run: Run = useCallback(
    async (action) => {
      try {
        await action();
        await refresh();
        return true;
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        return false;
      }
    },
    [refresh],
  );

  useEffect(() => {
    run(async () => undefined).finally(() => setLoaded(true));
  }, [run]);

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
          <Squad players={players} run={run} />
        ) : (
          <History matches={matches} />
        )}
      </main>

      {error && (
        <div className="toast" role="alert" onClick={() => setError(null)}>
          {error}
        </div>
      )}
    </div>
  );
}
