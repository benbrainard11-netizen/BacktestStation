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
