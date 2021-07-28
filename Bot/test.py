class x:
    def __init__(self, x) -> None:
        self.x = x


class y:
    def __init__(self, x) -> None:
        self.x = x

var = x(3)
var2 = y(var)
var.x = 4
print(var2.x.x)
var2.x.x = 5
print(var.x)
