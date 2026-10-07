import numpy as np

from lotto.merkmale import MERKMAL_NAMEN, merkmals_matrix, one_hot
from tests.hilfen import kuenstliche_ziehungen

H10, H50, H200, SEIT, RATE, LETZTE = range(6)


def test_one_hot():
    x = one_hot([(1, 2, 3, 4, 5, 6)])
    assert x.shape == (1, 49) and x.sum() == 6 and x[0, :6].all()


def test_werte_an_kleinem_beispiel():
    zahlen = [(1, 2, 3, 4, 5, 6), (1, 7, 8, 9, 10, 11), (12, 13, 14, 15, 16, 17)]
    f = merkmals_matrix(zahlen)
    assert f.shape == (3, 49, len(MERKMAL_NAMEN))
    assert f[0, :, H10].sum() == 0
    assert f[2, 0, H10] == 2 and f[2, 0, H200] == 2
    assert f[2, 0, SEIT] == 1
    assert f[2, 1, SEIT] == 2
    assert f[2, 48, SEIT] == 3
    assert f[2, 0, RATE] == 1.0
    assert f[2, 0, LETZTE] == 1 and f[2, 1, LETZTE] == 0


def test_kein_datenleck():
    zahlen = [z.zahlen for z in kuenstliche_ziehungen(300, seed=3)]
    original = merkmals_matrix(zahlen)
    for i in (0, 150, 299):
        geaendert = list(zahlen)
        geaendert[i] = (44, 45, 46, 47, 48, 49)
        assert np.array_equal(merkmals_matrix(geaendert)[: i + 1], original[: i + 1])
