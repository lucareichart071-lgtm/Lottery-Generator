from datetime import date, timedelta

import pytest

from lotto.backtest import STRATEGIEN, backtest
from tests.hilfen import kuenstliche_ziehungen

START = date(2000, 1, 1)


def _strategie(ergebnis, name):
    return next(s for s in ergebnis.strategien if s.name == name)


def test_findet_kuenstlich_eingebautes_muster():
    ziehungen = kuenstliche_ziehungen(1500, seed=1, fest=7, start=START)
    e = backtest(ziehungen, START + timedelta(days=1000), n_permutationen=500)
    for name in ("heiss", "modell"):
        s = _strategie(e, name)
        assert s.mittel_treffer > 1.3, name
        assert s.p_korrigiert < 0.05, name


def test_zufallsdaten_bleiben_im_erwartbaren_bereich():
    ziehungen = kuenstliche_ziehungen(1500, seed=2, start=START)
    e = backtest(ziehungen, START + timedelta(days=1000), n_permutationen=500)
    assert e.n_training == 800 and e.n_test == 500
    assert [s.name for s in e.strategien] == list(STRATEGIEN)
    for s in e.strategien:
        assert 0.6 < s.mittel_treffer < 0.87, s.name
        assert 0 < s.p_wert <= 1 and s.p_wert <= s.p_korrigiert <= 1
    assert abs(e.erwartet_mittel - 36 / 49) < 1e-12
    assert 0 <= e.chi2_p_wert <= 1


def test_zu_wenig_trainingsdaten():
    ziehungen = kuenstliche_ziehungen(300, start=START)
    with pytest.raises(ValueError, match="Trainings"):
        backtest(ziehungen, START + timedelta(days=100))


def test_ergebnis_ist_json_tauglich():
    import json

    ziehungen = kuenstliche_ziehungen(400, seed=4, start=START)
    e = backtest(ziehungen, START + timedelta(days=300), n_permutationen=50)
    daten = json.loads(json.dumps(e.als_dict()))
    assert daten["strategien"][0]["name"] == "zufall"
