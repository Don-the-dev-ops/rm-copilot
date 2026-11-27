const randFormatter = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** South African rand, e.g. R104,221.86. Negative values: -R52,174.30. */
export function formatRand(value: number): string {
  const sign = value < 0 ? "-" : "";
  return `${sign}R${randFormatter.format(Math.abs(value))}`;
}

/** Short rand for chart axes: R1.2m, R166k, R900. */
export function formatRandShort(value: number): string {
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `R${(value / 1_000_000).toFixed(abs >= 10_000_000 ? 0 : 1)}m`;
  if (abs >= 1_000) return `R${Math.round(value / 1_000)}k`;
  return `R${Math.round(value)}`;
}

export function formatPercent(share: number): string {
  return `${Math.round(share * 100)}%`;
}

const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function parts(iso: string) {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  const time = iso.length > 10 ? iso.slice(11, 16) : "";
  return { y, m, d, time };
}

/** "2026-11-27" -> "Friday 27 November 2026". Calendar date, no time zone shift. */
export function formatLongDate(iso: string): string {
  const { y, m, d } = parts(iso);
  const weekday = new Date(Date.UTC(y, m - 1, d)).getUTCDay();
  return `${WEEKDAYS[weekday]} ${d} ${MONTHS[m - 1]} ${y}`;
}

/** "2026-11-27T05:42:00" -> "27 Nov 2026". */
export function formatShortDate(iso: string): string {
  const { y, m, d } = parts(iso);
  return `${d} ${MONTHS[m - 1].slice(0, 3)} ${y}`;
}

/** "2026-11-27T05:42:00" -> "05:42". */
export function formatTime(iso: string): string {
  return parts(iso).time;
}

/** "2026-12-01" -> "Dec". */
export function formatMonthShort(iso: string): string {
  return MONTHS[parts(iso).m - 1].slice(0, 3);
}

/** "2026-11-01" -> "November 2026". */
export function formatMonthLong(iso: string): string {
  const { y, m } = parts(iso);
  return `${MONTHS[m - 1]} ${y}`;
}

const NUMBER_WORDS = ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"];

/** Spell out small counts at the start of a sentence: 5 -> "Five". */
export function countWord(n: number): string {
  return NUMBER_WORDS[n] ?? String(n);
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return n === 1 ? one : many;
}
