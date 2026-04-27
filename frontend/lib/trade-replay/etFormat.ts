/**
 * Eastern Time formatting helpers for the trade-replay chart.
 *
 * All futures markets (NQ/ES/YM/etc.) reference ET, and the live bot
 * writes its JSONL in ET. The DB stores tz-naive UTC. Replay needs to
 * surface ET to keep the user's mental model consistent across
 * BacktestStation, TradingView, and the bot's own logs.
 *
 * `Intl.DateTimeFormat` with `timeZone: 'America/New_York'` handles
 * EST/EDT transitions automatically — no DST math here.
 */

const ET_TIME_HMS = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/New_York",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

const ET_TIME_HM = new Intl.DateTimeFormat("en-US", {
  timeZone: "America/New_York",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
});

const ET_DATE = new Intl.DateTimeFormat("en-CA", {
  timeZone: "America/New_York",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

/**
 * Parse an ISO 8601 timestamp from the BacktestStation API as **UTC**.
 *
 * Tz-naive Pydantic datetimes serialize without a `Z` suffix
 * (`"2026-04-22T13:37:00"`). The native `new Date()` parser interprets
 * such strings as the browser's *local* time, which silently shifts
 * every trade timestamp by the user's UTC offset — that produced the
 * "entry marker is 7 hours past where the trade happened" bug. The
 * DB stores tz-naive UTC by convention, so we append `Z` when no zone
 * marker is present and let the parser do the right thing.
 *
 * Strings that already have `Z` or a `+HH:MM` / `-HH:MM` offset pass
 * through unchanged.
 */
export function parseUtcLoose(iso: string): Date {
  if (!iso) return new Date(NaN);
  if (iso.endsWith("Z") || /[+-]\d{2}:?\d{2}$/.test(iso)) {
    return new Date(iso);
  }
  return new Date(`${iso}Z`);
}

/** Same as parseUtcLoose, returning ms. Convenience for arithmetic. */
export function utcMs(iso: string): number {
  return parseUtcLoose(iso).getTime();
}

/** "13:31:24" given a millisecond epoch. */
export function etHMS(ms: number): string {
  return ET_TIME_HMS.format(new Date(ms));
}

/** "13:31" given a millisecond epoch. */
export function etHM(ms: number): string {
  return ET_TIME_HM.format(new Date(ms));
}

/** "2026-04-22" given a millisecond epoch. */
export function etDate(ms: number): string {
  return ET_DATE.format(new Date(ms));
}

/** "13:31:24 ET" — for tooltips + labels. */
export function etHMSLabel(ms: number): string {
  return `${etHMS(ms)} ET`;
}

/**
 * Lightweight-charts `localization.timeFormatter` callback. Receives a
 * `UTCTimestamp` (seconds since epoch). Returns the ET clock time.
 */
export function chartTimeFormatter(time: number): string {
  return etHM(time * 1000);
}

/**
 * Lightweight-charts `localization.dateFormat` doesn't accept a function
 * for date formatting; pass the formatter via `priceFormat` etc. as
 * needed. For tooltip-level dates, use `etDate` directly in JSX.
 */
