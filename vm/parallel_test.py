import multiprocessing
import numpy as np
from random import random
import time
manager = multiprocessing.Manager()

final_list = manager.list([0, 0])

# list = np.array([0.0, 0.0])


def func1():
    print('update: starting')
    while True:
        final_list[0] = np.round(random(), 4)
        final_list[1] = np.round(random(), 4)
        time.sleep(0.1)


def func2():
    print('func2: starting')
    while True:
        print(final_list)
        time.sleep(1)


if __name__ == '__main__':
    p1 = multiprocessing.Process(target=func1)
    p1.start()
    p2 = multiprocessing.Process(target=func2)
    p2.start()
    p1.join()
    p2.join()