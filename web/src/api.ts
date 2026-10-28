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

export interface Player {
  name: string;
  skills: Skills;
  form: number;
  rating: number;
}

export interface Team {
  players: Player[];
  bonus: number;
  rating: number;
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

/**
 * Sends a request and returns the parsed JSON body. Throws ApiError with the
 * API's `detail` message for any non-2xx response.
 */
async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
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
  listPlayers: () => request<Player[]>("GET", "/players"),
  addPlayer: (name: string, skills: Skills) =>
    request<Player>("POST", "/players", { name, skills }),
  updatePlayer: (name: string, changes: PlayerChanges) =>
    request<Player>("PATCH", playerPath(name), changes),
  removePlayer: (name: string) => request<void>("DELETE", playerPath(name)),

  listMatches: () => request<Match[]>("GET", "/matches"),
  createMatch: (players: string[]) => request<Match>("POST", "/matches", { players }),
  cancelMatch: (id: number) => request<void>("DELETE", `/matches/${id}`),
  recordResult: (id: number, winner: TeamKey) =>
    request<Match>("PUT", `/matches/${id}/result`, { winner }),
};
