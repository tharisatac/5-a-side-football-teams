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

/** Form 5 is neutral: above is in form, below is out of form. */
export function formTrend(form: number): "up" | "down" | "flat" {
  return form > 5 ? "up" : form < 5 ? "down" : "flat";
}
