"""Example strategies for testing the engine. Not real trading
strategies; they exist to prove the Strategy interface works."""

from app.strategies.examples.moving_average_crossover import (
    MovingAverageCrossover,
)

__all__ = ["MovingAverageCrossover"]
