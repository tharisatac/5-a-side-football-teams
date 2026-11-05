// Typed client for the FastAPI backend (src/api.py). The types mirror the
// API's Pydantic response models, so TypeScript catches a mistyped field.

export const SKILLS = [
  "shooting",
  "dribbling",
  "passing",
  "tackling",
  "fitness",
  "goalkeeping",
] as const;

export type SkillName = (typeof SKILLS)[number];
export type Skills = Record<SkillName, number>;
export type TeamKey = "team1" | "team2";

// Skills, form and ratings are null unless the passcode was sent: anyone
// can view, but only the organisers see the numbers.
export interface Player {
  name: string;
  skills: Skills | null;
  form: number | null;
  rating: number | null;
}

export interface Team {
  players: Player[];
  bonus: number;
  rating: number | null;
}

export interface Match {
  id: number;
  created_at: string;
  team1: Team;
  team2: Team;
  winner: TeamKey | null;
}

export type PlayerChanges = Partial<Skills> & { form?: number };

/** An error response from the API, with its status code and message. */
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

// The shared passcode, remembered on this device so it's
// only typed once. Storage can be unavailable (e.g. private browsing), so
// every access is guarded; without it the passcode lasts until a reload.
const PASSCODE_KEY = "passcode";
let passcode: string | null = (() => {
  try {
    return localStorage.getItem(PASSCODE_KEY);
  } catch {
    return null;
  }
})();

/** The remembered passcode, or null if this device is locked. */
export const getPasscode = () => passcode;

/** Remembers a passcode, or forgets it with null. */
export function setPasscode(value: string | null) {
  passcode = value;
  try {
    if (value === null) localStorage.removeItem(PASSCODE_KEY);
    else localStorage.setItem(PASSCODE_KEY, value);
  } catch {
    // Not remembered across reloads, which is fine.
  }
}

/**
 * Sends a request and returns the parsed JSON body. Throws ApiError with the
 * API's `detail` message for any non-2xx response.
 */
async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers["Content-Type"] = "application/json";
  // Sent with every request: changes need it, and reads include the
  // ratings only when it's there.
  if (passcode !== null) headers["Authorization"] = `Bearer ${passcode}`;
  const response = await fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    throw new ApiError(response.status, await errorMessage(response));
  }
  // 204 No Content has no body to parse.
  return (response.status === 204 ? undefined : await response.json()) as T;
}

/**
 * Our own errors send `{"detail": "message"}`; Pydantic validation errors send
 * `{"detail": [{"msg": ...}, ...]}`. Returns a readable message for either.
 */
async function errorMessage(response: Response): Promise<string> {
  try {
    const { detail } = await response.json();
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((d) => d.msg).join("; ");
  } catch {
    // Not JSON, e.g. the API isn't running and the proxy returned an error.
  }
  return `Request failed (${response.status} ${response.statusText})`;
}

const playerPath = (name: string) => `/players/${encodeURIComponent(name)}`;

export const api = {
  /** Resolves if `candidate` is the right passcode; throws ApiError if not. */
  checkPasscode: async (candidate: string) => {
    const response = await fetch("/auth/check", {
      headers: { Authorization: `Bearer ${candidate}` },
    });
    if (!response.ok) throw new ApiError(response.status, await errorMessage(response));
  },

  listPlayers: () => request<Player[]>("GET", "/players"),
  addPlayer: (name: string, skills: Skills) =>
    request<Player>("POST", "/players", { name, skills }),
  updatePlayer: (name: string, changes: PlayerChanges) =>
    request<Player>("PATCH", playerPath(name), changes),
  removePlayer: (name: string) => request<void>("DELETE", playerPath(name)),
  resetForms: () => request<Player[]>("POST", "/players/reset-forms"),

  listMatches: () => request<Match[]>("GET", "/matches"),
  createMatch: (players: string[]) => request<Match>("POST", "/matches", { players }),
  deleteMatch: (id: number) => request<void>("DELETE", `/matches/${id}`),
  swapPlayers: (id: number, first: string, second: string) =>
    request<Match>("POST", `/matches/${id}/swap`, { players: [first, second] }),
  recordResult: (id: number, winner: TeamKey) =>
    request<Match>("PUT", `/matches/${id}/result`, { winner }),
  clearResult: (id: number) => request<Match>("DELETE", `/matches/${id}/result`),
};
