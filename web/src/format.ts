import type { Match } from "./api";

// Small display helpers shared by the components.

/** "Ben Smith" -> "BS", "Tempy" -> "TE". */
export function initials(name: string): string {
  const words = name.trim().split(/\s+/);
  const letters = words.length > 1 ? words[0][0] + words[1][0] : name.slice(0, 2);
  return letters.toUpperCase();
}

/** Ratings to one decimal place, as on the CLI. */
export function rating(value: number): string {
  return value.toFixed(1);
}

/** "2026-10-28T19:26:49Z" -> "28 Oct 2026", in the viewer's time zone. */
export function matchDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

/**
 * How a match is named in the UI: its date, plus the time if another match
 * is on the same day, e.g. "28 Oct 2026, 19:41". Match IDs stay internal.
 */
export function matchLabel(match: Match, matches: Match[]): string {
  const date = matchDate(match.created_at);
  const sameDay = matches.some(
    (other) => other.id !== match.id && matchDate(other.created_at) === date,
  );
  if (!sameDay) return date;
  const time = new Date(match.created_at).toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
  });
  return `${date}, ${time}`;
}

/** Form 5 is neutral: above is in form, below is out of form. */
export function formTrend(form: number): "up" | "down" | "flat" {
  return form > 5 ? "up" : form < 5 ? "down" : "flat";
}
