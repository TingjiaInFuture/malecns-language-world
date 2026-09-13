"""Integer-tick subsystem scheduler; rendering never advances this clock."""
from fractions import Fraction


class MultiClock:
    def __init__(self, base_ms, periods_ms):
        base = Fraction(str(base_ms))
        if base <= 0:
            raise ValueError('Clock base must be positive')
        self.base_ms, self.tick = float(base), 0
        self.periods = {}
        for name, period in periods_ms.items():
            ratio = Fraction(str(period))/base
            if ratio.denominator != 1 or ratio <= 0:
                raise ValueError('Subsystem period must be a positive integer number of ticks')
            self.periods[name] = int(ratio)

    def advance(self):
        self.tick += 1
        return tuple(name for name, period in self.periods.items() if self.tick % period == 0)
