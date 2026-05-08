"""CME Globex session math.

Pure functions, no IO. Used by every detector that needs "previous
week" / "previous day" reference periods aligned to the actual futures
trading session, not the calendar week/day.

Globex futures trade Sunday 18:00 ET → Friday 17:00 ET, with a 60-min
maintenance break each day from 17:00 → 18:00 ET. For SMT-style
research, we treat:

  - **Globex week**: Sunday 18:00 ET → Friday 17:00 ET (continuous
    24/5 plus the Sunday evening overnight session).
  - **Globex day**: 18:00 ET previous calendar day → 17:00 ET current
    calendar day. Sunday's session belongs to Monday's day. The
    Friday 17:00 close ends the Friday session; Saturday has no
    session.

All boundary functions return tz-aware UTC datetimes. ET is canonical
input timezone for human reasoning, UTC is canonical storage.

Cross-link: docs/RESEARCH_KNOWLEDGE_LAYER.md (the surrounding
taxonomy), docs/RESEARCH_DETECTORS.md (how detectors use this).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
UTC = timezone.utc

# Globex day starts at 18:00 ET the previous calendar day.
GLOBEX_DAY_START_HOUR_ET: int = 18
# Globex day ends at 17:00 ET (also where the maintenance window starts).
GLOBEX_DAY_END_HOUR_ET: int = 17


@dataclass(frozen=True, slots=True)
class GlobexPeriod:
    """A bounded Globex period: [start_utc, end_utc).

    Bounds are HALF-OPEN to match standard timeseries slicing semantics:
    `start_utc` is included, `end_utc` is excluded. Both are tz-aware
    UTC.
    """

    start_utc: datetime
    end_utc: datetime
    label: str  # "globex_week" or "globex_day"

    def contains(self, ts: datetime) -> bool:
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        return self.start_utc <= ts < self.end_utc


# ---------- Day boundaries ----------


def globex_day_for(ref: datetime) -> GlobexPeriod:
    """Return the Globex day that CONTAINS `ref`.

    Examples (ET):
      - Tuesday 14:00 → Mon 18:00 → Tue 17:00
      - Tuesday 17:30 → Tue 18:00 → Wed 17:00 (maintenance window
        belongs to the NEXT Globex day's start)
      - Tuesday 18:00 → Tue 18:00 → Wed 17:00
      - Sunday 19:00 → Sun 18:00 → Mon 17:00
      - Saturday or Sunday <18:00 → previous Friday's session is
        already closed; we return the upcoming Sunday-anchored session
        (Sun 18:00 → Mon 17:00) for the closest Saturday case, with
        the Sunday-pre-18:00 case rolling forward to the same.

    Saturday + early-Sunday handling: there is no Globex session
    between Fri 17:00 and Sun 18:00. We treat any timestamp in that
    gap as belonging to the NEXT session (Sunday 18:00 onward) so
    callers asking "what session is this in" get a forward-looking
    answer, not a closed historical session.
    """
    et = _to_et(ref)
    weekday = et.weekday()  # Mon=0 .. Sun=6
    et_time = et.time()

    # Saturday (5) → no session today. Roll forward to Sun 18:00.
    if weekday == 5:
        sun_18 = datetime.combine(
            et.date() + timedelta(days=1),
            time(GLOBEX_DAY_START_HOUR_ET),
            tzinfo=ET,
        )
        return _period_from_start_et(sun_18, "globex_day")

    # Sunday before 18:00 → no session yet. Roll forward to today 18:00.
    if weekday == 6 and et_time < time(GLOBEX_DAY_START_HOUR_ET):
        start_et = datetime.combine(
            et.date(), time(GLOBEX_DAY_START_HOUR_ET), tzinfo=ET
        )
        return _period_from_start_et(start_et, "globex_day")

    # Sunday 18:00+ → Sun 18:00 → Mon 17:00.
    if weekday == 6:
        start_et = datetime.combine(
            et.date(), time(GLOBEX_DAY_START_HOUR_ET), tzinfo=ET
        )
        return _period_from_start_et(start_et, "globex_day")

    # Mon-Fri before 17:00 → today's Globex day is from yesterday 18:00
    # → today 17:00.
    if et_time < time(GLOBEX_DAY_END_HOUR_ET):
        start_et = datetime.combine(
            et.date() - timedelta(days=1),
            time(GLOBEX_DAY_START_HOUR_ET),
            tzinfo=ET,
        )
        return _period_from_start_et(start_et, "globex_day")

    # Mon-Fri at or after 17:00 → maintenance window belongs to the
    # NEXT Globex day. Friday 17:00+ is awkward: there's no Friday-
    # evening session; roll forward to Sun 18:00.
    if weekday == 4:  # Friday
        days_to_sunday = (6 - weekday) % 7  # 2
        sun_18 = datetime.combine(
            et.date() + timedelta(days=days_to_sunday),
            time(GLOBEX_DAY_START_HOUR_ET),
            tzinfo=ET,
        )
        return _period_from_start_et(sun_18, "globex_day")

    # Mon-Thu at 17:00-18:00 → next session starts today 18:00.
    start_et = datetime.combine(et.date(), time(GLOBEX_DAY_START_HOUR_ET), tzinfo=ET)
    return _period_from_start_et(start_et, "globex_day")


def previous_globex_day(ref: datetime) -> GlobexPeriod:
    """Return the Globex day immediately preceding the one containing
    `ref`. Friday's previous-day is Thursday's session; Monday's
    previous-day is Friday's (skipping the weekend). Sunday-evening
    sessions count as Monday's day, so their previous-day is Friday.

    Implemented via direct calendar arithmetic on the current
    session's start_date in ET, NOT a probe — probes land in the
    maintenance window or the weekend gap and `globex_day_for`
    rolls them forward, returning the same period.
    """
    current = globex_day_for(ref)
    cur_start_et = current.start_utc.astimezone(ET)
    cur_start_date = cur_start_et.date()
    cur_weekday = cur_start_date.weekday()  # Mon=0..Sun=6
    # Globex day starts (in ET) only ever land on weekdays Sun, Mon,
    # Tue, Wed, Thu (Sun→Mon's session, Mon→Tue's session, etc.).
    # Sunday → step back 3 days (skipping Sat/Fri-evening gap) to the
    # Thursday that opens Fri's session. Otherwise step back 1 day.
    if cur_weekday == 6:  # Sunday — current is Mon's session
        prev_start_date = cur_start_date - timedelta(days=3)
    else:
        prev_start_date = cur_start_date - timedelta(days=1)
    prev_start_et = datetime.combine(
        prev_start_date, time(GLOBEX_DAY_START_HOUR_ET), tzinfo=ET
    )
    prev_end_et = datetime.combine(
        prev_start_date + timedelta(days=1),
        time(GLOBEX_DAY_END_HOUR_ET),
        tzinfo=ET,
    )
    return GlobexPeriod(
        start_utc=prev_start_et.astimezone(UTC),
        end_utc=prev_end_et.astimezone(UTC),
        label="globex_day",
    )


# ---------- Week boundaries ----------


def globex_week_for(ref: datetime) -> GlobexPeriod:
    """Return the Globex week that contains `ref`.

    Globex week = Sunday 18:00 ET → Friday 17:00 ET. Saturday and
    Sunday before 18:00 are between weeks; we roll those forward to
    the next Sunday 18:00 (consistent with `globex_day_for`).
    """
    et = _to_et(ref)
    weekday = et.weekday()  # Mon=0..Sun=6
    et_time = et.time()

    # Find the Sunday 18:00 that opens this week.
    if weekday == 6 and et_time >= time(GLOBEX_DAY_START_HOUR_ET):
        # Sunday after 18:00 → THIS Sunday opens the week.
        sun_18 = datetime.combine(
            et.date(), time(GLOBEX_DAY_START_HOUR_ET), tzinfo=ET
        )
    elif weekday == 5:
        # Saturday → roll forward to tomorrow's Sun 18:00.
        sun_18 = datetime.combine(
            et.date() + timedelta(days=1),
            time(GLOBEX_DAY_START_HOUR_ET),
            tzinfo=ET,
        )
    elif weekday == 6 and et_time < time(GLOBEX_DAY_START_HOUR_ET):
        # Early Sunday → today's Sun 18:00 opens the week.
        sun_18 = datetime.combine(
            et.date(), time(GLOBEX_DAY_START_HOUR_ET), tzinfo=ET
        )
    elif weekday == 4 and et_time >= time(GLOBEX_DAY_END_HOUR_ET):
        # Friday after 17:00 → roll forward to next Sunday.
        sun_18 = datetime.combine(
            et.date() + timedelta(days=2),
            time(GLOBEX_DAY_START_HOUR_ET),
            tzinfo=ET,
        )
    else:
        # Mon-Fri (or Friday before 17:00): step back to most recent
        # Sunday.
        days_back = (weekday + 1) % 7  # Mon=0→1, Tue=1→2, ..., Fri=4→5
        sun_18 = datetime.combine(
            et.date() - timedelta(days=days_back),
            time(GLOBEX_DAY_START_HOUR_ET),
            tzinfo=ET,
        )

    # Friday 17:00 ET closes the week.
    fri_17 = datetime.combine(
        sun_18.date() + timedelta(days=5),
        time(GLOBEX_DAY_END_HOUR_ET),
        tzinfo=ET,
    )
    return GlobexPeriod(
        start_utc=sun_18.astimezone(UTC),
        end_utc=fri_17.astimezone(UTC),
        label="globex_week",
    )


def previous_globex_week(ref: datetime) -> GlobexPeriod:
    """Return the Globex week immediately preceding the one containing
    `ref`. End of previous week is the Friday before this week's
    Sunday open.

    Direct arithmetic on `current.start_utc` (always Sun 18:00 ET) —
    step back exactly 7 days. Avoids the probe-trap where the
    microsecond before this week's start lands in the Sun-pre-18:00
    gap and `globex_week_for` rolls forward back to the same week.
    """
    current = globex_week_for(ref)
    return GlobexPeriod(
        start_utc=current.start_utc - timedelta(days=7),
        end_utc=current.end_utc - timedelta(days=7),
        label="globex_week",
    )


# ---------- Internals ----------


def _to_et(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    return ts.astimezone(ET)


def _period_from_start_et(start_et: datetime, label: str) -> GlobexPeriod:
    """Given a Globex day start (always 18:00 ET on some calendar
    date), build the period ending at 17:00 ET the NEXT calendar
    day. Friday-anchored starts (which would imply Sat 17:00) get
    closed at 17:00 ET on the same day — handled by callers, not
    here."""
    end_et = datetime.combine(
        start_et.date() + timedelta(days=1),
        time(GLOBEX_DAY_END_HOUR_ET),
        tzinfo=ET,
    )
    return GlobexPeriod(
        start_utc=start_et.astimezone(UTC),
        end_utc=end_et.astimezone(UTC),
        label=label,
    )
