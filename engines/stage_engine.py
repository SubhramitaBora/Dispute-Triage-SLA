# engines/stage_engine.py

class StageStuckEngine:

    def __init__(self):
        self.weights = {
            1: 1,
            2: 1,
            3: 7,
            4: 5,
            5: 10
        }

    def compute(self, stage: int, days_open: int):
        weight = self.weights.get(stage, 1)
        return weight, weight * max(days_open, 1)
