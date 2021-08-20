class x:
    def __init__(self) -> None:
        self.y = 45

z = x()
g = [z]

h = g[-1]

h.y += 1

print(z.y, g[0].y, h.y)
