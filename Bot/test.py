import datetime
import time
x = datetime.datetime.now()
time.sleep(2.3)
dif = datetime.datetime.now() - x
print(dif.seconds + dif.microseconds / 1000000)