# NQ Opening-Range Descriptive Study

## Purpose

This is a descriptive study of NQ opening-range behavior.

It does not build a strategy and does not optimize thresholds.

The study defines the opening range as 09:30-10:00 ET, then studies the first break of the opening-range high or low after 10:00 ET.

## Definition

Opening range:

- Start: 09:30 ET
- End: 10:00 ET
- High: highest 1-minute bar high inside the window
- Low: lowest 1-minute bar low inside the window
- Range: high minus low

First break:

- High break: first post-10:00 bar where high trades above the opening-range high
- Low break: first post-10:00 bar where low trades below the opening-range low
- If both happen in the same 1-minute bar, the event is ambiguous

Outcome label:

- High-break continuation target: `OR high + OR range`
- High-break reversal target: `OR low`
- Low-break continuation target: `OR low - OR range`
- Low-break reversal target: `OR high`

The target distance is exactly one opening-range width. This is fixed and volatility-adjusted without tuning.

If continuation and reversal targets are both touched in the same 1-minute bar, the label is ambiguous.

## Data Used

Generated local output:

`data/backtests/nq_opening_range_descriptive_2025-05-01_2026-05-23`

Files:

- `opening_range_descriptive_events.csv`
- `opening_range_descriptive_baseline.csv`
- `opening_range_descriptive_contexts.csv`
- `opening_range_descriptive_consistency.csv`
- `opening_range_descriptive_context_validation.csv`
- `opening_range_descriptive_walk_forward.csv`
- `opening_range_descriptive_monthly.csv`
- `opening_range_descriptive_config.csv`
- `opening_range_descriptive_summary.json`

Study window:

- Start: 2025-05-01
- End: 2026-05-23 available window
- Holdout split: 2026-02-01
- Sessions analyzed: 270

## Baseline Results

| Scope | Sessions | Labeled | Continuations | Reversals | Ambiguous | Continuation Rate |
|---|---:|---:|---:|---:|---:|---:|
| Full | 270 | 179 | 95 | 84 | 90 | 53.1% |
| In-sample | 192 | 126 | 67 | 59 | 65 | 53.2% |
| Holdout | 78 | 53 | 28 | 25 | 25 | 52.8% |

Beginner read: simple opening-range continuation was only slightly better than 50/50. The holdout stayed similar to in-sample, but the effect is not large.

## High Breaks Vs Low Breaks

| Scope | First Break | Sessions | Labeled | Continuation Rate |
|---|---|---:|---:|---:|
| Full | High first | 151 | 93 | 50.5% |
| Full | Low first | 118 | 86 | 55.8% |
| In-sample | High first | 103 | 64 | 50.0% |
| In-sample | Low first | 88 | 62 | 56.5% |
| Holdout | High first | 48 | 29 | 51.7% |
| Holdout | Low first | 30 | 24 | 54.2% |

Low breaks had a slightly higher continuation rate than high breaks in both in-sample and holdout.

This is directionally consistent, but not a strong edge by itself.

## Stable Contexts

The most directionally consistent contexts were opening-drive behavior and first-break side.

| Context | IS Continuation | IS Delta | HO Continuation | HO Delta | Read |
|---|---:|---:|---:|---:|---|
| First break low | 56.5% | +3.3 pp | 54.2% | +1.3 pp | Mildly stable |
| First break high | 50.0% | -3.2 pp | 51.7% | -1.1 pp | Mildly stable lower |
| Opening drive down | 54.0% | +0.8 pp | 71.4% | +18.6 pp | Stable, stronger holdout |
| Opening drive up | 45.0% | -8.2 pp | 44.4% | -8.4 pp | Stable lower |
| OR close lower third | 54.1% | +0.9 pp | 58.8% | +6.0 pp | Stable but mild |
| OR close middle third | 61.9% | +8.7 pp | 68.8% | +15.9 pp | Stable positive |
| OR close upper third | 44.7% | -8.5 pp | 35.0% | -17.8 pp | Stable negative |

Beginner read: when the opening drive closed high in its own range, later OR continuation was worse. When the opening drive closed middle or lower, continuation was better. Down opening drives were also more continuation-friendly than up opening drives in this sample.

## Unstable Contexts

Overnight trend and RTH gap direction did not survive cleanly:

| Context | IS Direction | Holdout Direction | Read |
|---|---|---|---|
| Overnight trend down | Higher continuation | Lower continuation | Inconsistent |
| Overnight trend up | Lower continuation | Higher continuation | Inconsistent |
| RTH gap down | Higher continuation | Lower continuation | Inconsistent |
| RTH gap up | Lower continuation | Higher continuation | Inconsistent |

Beginner read: overnight trend and gap direction may matter in some regimes, but they were not stable enough here to justify future strategy research by themselves.

## Monthly Behavior

Continuation rates varied a lot by month:

| Month | Sessions | Labeled | Continuation Rate |
|---|---:|---:|---:|
| 2025-05 | 22 | 15 | 46.7% |
| 2025-06 | 20 | 18 | 38.9% |
| 2025-07 | 23 | 15 | 46.7% |
| 2025-08 | 21 | 12 | 58.3% |
| 2025-09 | 21 | 13 | 69.2% |
| 2025-10 | 23 | 17 | 58.8% |
| 2025-11 | 20 | 11 | 36.4% |
| 2025-12 | 21 | 13 | 46.2% |
| 2026-01 | 21 | 12 | 83.3% |
| 2026-02 | 20 | 11 | 63.6% |
| 2026-03 | 21 | 15 | 46.7% |
| 2026-04 | 21 | 16 | 56.3% |
| 2026-05 | 16 | 11 | 45.5% |

Beginner read: the average was stable, but month-to-month behavior was not smooth. That means any future strategy research should use walk-forward validation and should not trust one strong month.

## Main Findings

1. Simple OR continuation was slightly positive but weak.
   Full continuation rate was 53.1%, and holdout was 52.8%.

2. Low breaks were modestly more continuation-friendly than high breaks.
   This held in-sample and holdout, but the difference was small.

3. Opening-drive behavior was the most interesting context.
   Down opening drives and middle/lower OR closes were more continuation-friendly. Upper-third OR closes were less continuation-friendly.

4. Overnight trend and RTH gap direction were not stable.
   They flipped direction between in-sample and holdout.

5. Ambiguity was common.
   90 of 270 sessions were ambiguous under 1-minute bar sequencing. That is a real limitation and should not be ignored.

## Conclusion

The opening-range study found descriptive patterns worth future research, especially around opening-drive behavior.

The strongest future-research candidates are:

- OR close in the middle third
- avoiding continuation assumptions when the OR closes in the upper third
- first OR low break continuation as a mild, smaller secondary hint

This is not enough to build a strategy yet. The next step should be a frozen follow-up study that predeclares one or two simple context hypotheses and validates them out of sample.

See `docs/NQ_OPENING_RANGE_CONTEXT_VALIDATION.md` for the stricter holdout and walk-forward context validation.
