s = " w w  w   w    w     w      w ".replace("  ", " ")
while s.find("  ") != -1:
    s = s.replace("  ", " ")
print(s)