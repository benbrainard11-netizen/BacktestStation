"""NaiveBaseline — predicts marginal class frequency from training data.

Sanity-floor baseline. If a real model can't beat this consistently, the
real model is broken.

For each (symbol, horizon), compute the empirical class distribution on the
training fold. Predict that distribution for every row in val/test.

NOT YET IMPLEMENTED.
"""

from __future__ import annotations


def main() -> int:
    raise NotImplementedError("baseline_naive.py is a stub.")


if __name__ == "__main__":
    raise SystemExit(main())
