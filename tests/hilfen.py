import random
from datetime import date, timedelta

from lotto.daten import Ziehung


def kuenstliche_ziehungen(n, seed=0, fest=None, start=date(2000, 1, 1)):
    """n zufällige Ziehungen; mit `fest` ist diese Zahl in jeder Ziehung."""
    rng = random.Random(seed)
    ziehungen = []
    for i in range(n):
        if fest is None:
            zahlen = rng.sample(range(1, 50), 6)
        else:
            zahlen = rng.sample([z for z in range(1, 50) if z != fest], 5) + [fest]
        ziehungen.append(
            Ziehung(start + timedelta(days=i), tuple(sorted(zahlen)), rng.randint(0, 9))
        )
    return ziehungen


def als_csv(ziehungen):
    zeilen = ["date,n1,n2,n3,n4,n5,n6,superzahl"]
    for z in ziehungen:
        sz = "" if z.superzahl is None else str(z.superzahl)
        zeilen.append(",".join([z.datum.isoformat(), *map(str, z.zahlen), sz]))
    return "\n".join(zeilen) + "\n"
