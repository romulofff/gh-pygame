class Score():
    def __init__(self, SCREEN_WIDTH=None, decrease_mode=False):
        self.value = 0
        self.x_pos = 100
        self.font_size = 25
        self.decrease_mode = decrease_mode

        # The ammount of notes correctly hit in a row
        self._counter = 0

        self.rock_meter = 50

    def hit(self, value=10):
        self._counter = min(self._counter + 1, 39)
        self.value += value * self.multiplier

        self.rock_meter = min(self.rock_meter + 2, 100)

    def miss(self):
        self._counter = 0
        self.rock_meter -= 2
        if self.rock_meter <= 0:
            global done
            done = True
        else:
            done = False
        return done

    def miss_click(self):
        done = self.miss()
        self.value -= 10 * self.decrease_mode
        return done

    @property
    def counter(self):
        return self._counter + 1

    @property
    def multiplier(self):
        return 1 + self._counter // 10