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


def trading_date_for(ref: datetime) -> date:
    """Return the ET trading-date label for the Globex day containing `ref`.

    The label is the local ET date of the 17:00 Globex close. For example,
    Sun 18:00 ET -> Mon 17:00 ET is labeled Monday.
    """
    return globex_day_for(ref).end_utc.astimezone(ET).date()


def globex_day_for_trading_date(trading_day: date) -> GlobexPeriod:
    """Return the full Globex day labeled by `trading_day`.

    `trading_day` is the ET date of the session close:
    Monday = Sunday 18:00 ET -> Monday 17:00 ET.
    """
    if trading_day.weekday() >= 5:
        raise ValueError("Globex trading day labels must be Monday-Friday")
    start_et = datetime.combine(
        trading_day - timedelta(days=1),
        time(GLOBEX_DAY_START_HOUR_ET),
        tzinfo=ET,
    )
    end_et = datetime.combine(
        trading_day,
        time(GLOBEX_DAY_END_HOUR_ET),
        tzinfo=ET,
    )
    return GlobexPeriod(
        start_utc=start_et.astimezone(UTC),
        end_utc=end_et.astimezone(UTC),
        label="globex_day",
    )


def previous_trading_date(trading_day: date) -> date:
    """Previous weekday trading-date label, skipping Saturday/Sunday."""
    if trading_day.weekday() >= 5:
        raise ValueError("trading_day must be Monday-Friday")
    prev = trading_day - timedelta(days=1)
    while prev.weekday() >= 5:
        prev -= timedelta(days=1)
    return prev


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


# ---------- Intraday session boundaries (Asia / London / NY) ----------
#
# Convention chosen 2026-05-09: three non-overlapping sessions covering
# the Globex day. Within a Globex day (18:00 ET → 17:00 ET next):
#   asia:    18:00 ET (start of Globex day) → 02:00 ET (next morning)
#   london:  02:00 ET → 09:30 ET
#   ny:      09:30 ET → 17:00 ET (Globex day close)
#
# These are simple, non-killzone boundaries — wider than ICT killzones
# but much easier to reason about. Each session belongs to a SPECIFIC
# Globex day. All boundaries are tz-aware UTC.

ASIA_END_HOUR_ET: int = 2          # 02:00 ET = end of asia / start of london
LONDON_END_HOUR_ET: int = 9        # 09:00 ET → adjusted with minute=30 below
LONDON_END_MIN_ET: int = 30        # 09:30 ET = end of london / start of NY
# NY end = GLOBEX_DAY_END_HOUR_ET = 17:00 ET


def session_for(ref: datetime, session_name: str) -> GlobexPeriod:
    """Return the (asia | london | ny) session period that CONTAINS `ref`.

    The returned period is tied to the Globex day that contains `ref`.
    Within Globex day 18:00 ET → 17:00 ET next:
      - asia:    18:00 ET → 02:00 ET (8 hours, crosses midnight)
      - london:  02:00 ET → 09:30 ET
      - ny:      09:30 ET → 17:00 ET

    If `ref` falls between sessions (e.g. exactly at a boundary), it
    rolls forward to the start of the next session.
    """
    if session_name not in ("asia", "london", "ny"):
        raise ValueError(f"unknown session: {session_name!r}")
    day = globex_day_for(ref)
    day_start_et = day.start_utc.astimezone(ET)  # 18:00 ET (or Sun 18:00)
    asia_end_et = datetime.combine(
        day_start_et.date() + timedelta(days=1),
        time(ASIA_END_HOUR_ET),
        tzinfo=ET,
    )
    london_end_et = datetime.combine(
        day_start_et.date() + timedelta(days=1),
        time(LONDON_END_HOUR_ET, LONDON_END_MIN_ET),
        tzinfo=ET,
    )
    ny_end_et = datetime.combine(
        day_start_et.date() + timedelta(days=1),
        time(GLOBEX_DAY_END_HOUR_ET),
        tzinfo=ET,
    )
    if session_name == "asia":
        start_et, end_et = day_start_et, asia_end_et
    elif session_name == "london":
        start_et, end_et = asia_end_et, london_end_et
    else:
        start_et, end_et = london_end_et, ny_end_et
    return GlobexPeriod(
        start_utc=start_et.astimezone(UTC),
        end_utc=end_et.astimezone(UTC),
        label=f"session_{session_name}",
    )


def session_for_trading_date(trading_day: date, session_name: str) -> GlobexPeriod:
    """Return an intraday session inside a specific Globex trading day."""
    day = globex_day_for_trading_date(trading_day)
    return session_for(day.start_utc + timedelta(hours=1), session_name)


def rth_session_for_trading_date(
    trading_day: date,
    *,
    end_hour: int = 16,
    end_minute: int = 0,
) -> GlobexPeriod:
    """Return the cash/RTH session for a Globex trading-date label.

    Default RTH is 09:30-16:00 ET. This is intentionally separate from
    the `ny` Globex session, which runs 09:30-17:00 ET in this research
    taxonomy.
    """
    if trading_day.weekday() >= 5:
        raise ValueError("RTH trading day labels must be Monday-Friday")
    start_et = datetime.combine(trading_day, time(9, 30), tzinfo=ET)
    end_et = datetime.combine(trading_day, time(end_hour, end_minute), tzinfo=ET)
    if end_et <= start_et:
        raise ValueError("RTH end must be after 09:30 ET")
    return GlobexPeriod(
        start_utc=start_et.astimezone(UTC),
        end_utc=end_et.astimezone(UTC),
        label="session_rth",
    )


def previous_session(ref: datetime, session_name: str) -> GlobexPeriod:
    """Return the most recent COMPLETED session of the given name
    before `ref`.

    Iterates backward by Globex day. Within the same Globex day:
    - For ny ref, prev_ny is from the PREVIOUS Globex day (today's NY
      hasn't closed yet at the time of this call necessarily).
    - For asia ref, the previous asia is the previous Globex day's asia.
    Etc.

    Implementation: get the session for THIS Globex day; if its end
    is before `ref`, return it. Otherwise return the same session of
    the previous Globex day.
    """
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=UTC)
    this_day_session = session_for(ref, session_name)
    if this_day_session.end_utc <= ref:
        return this_day_session
    # Else look at previous Globex day's session.
    prev_day = previous_globex_day(ref)
    # Build the same-named session for that prior day's day_start.
    return session_for(prev_day.start_utc + timedelta(hours=1), session_name)
