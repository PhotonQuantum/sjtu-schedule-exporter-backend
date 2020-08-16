import collections
import datetime
from typing import List, Tuple, Union

lesson_time = ((datetime.time(8, 0), datetime.time(8, 45)),
               (datetime.time(8, 55), datetime.time(9, 40)),
               (datetime.time(10, 0), datetime.time(10, 45)),
               (datetime.time(10, 55), datetime.time(11, 40)),
               (datetime.time(12, 0), datetime.time(12, 45)),
               (datetime.time(12, 55), datetime.time(13, 40)),
               (datetime.time(14, 0), datetime.time(14, 45)),
               (datetime.time(14, 55), datetime.time(15, 40)),
               (datetime.time(16, 0), datetime.time(16, 45)),
               (datetime.time(16, 55), datetime.time(17, 40)),
               (datetime.time(18, 0), datetime.time(18, 45)),
               (datetime.time(18, 55), datetime.time(19, 40)),
               (datetime.time(19, 55), datetime.time(20, 40)),
               (datetime.time(20, 55), datetime.time(21, 40)))


def get_lesson_time(time: Union[int, List[int]]) -> Tuple[datetime.time, datetime.time]:
    if isinstance(time, int):
        return lesson_time[time - 1]
    elif isinstance(time, list):
        return lesson_time[time[0] - 1][0], lesson_time[time[-1] - 1][1]


def flatten(obj):
    for el in obj:
        if isinstance(el, collections.abc.Iterable) and not isinstance(el, (str, bytes)):
            yield from flatten(el)
        else:
            yield el
