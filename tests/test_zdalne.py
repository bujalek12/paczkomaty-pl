"""Testy pobierania agregatow z wydania "dane" (aplikacja w chmurze)."""

import httpx
import pytest

from paczkomaty.http import BladPobierania
from paczkomaty.zdalne import PLIKI, pobierz_z_wydania


def test_pobiera_wszystkie_pliki(tmp_path):
    klient = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, content=r.url.path.encode())))

    pobierz_z_wydania(tmp_path, klient=klient, czekaj=lambda s: None)

    for nazwa in PLIKI:
        assert (tmp_path / nazwa).read_bytes().endswith(nazwa.encode())


def test_przerwane_pobieranie_nie_psuje_starego_pliku(tmp_path):
    (tmp_path / PLIKI[0]).write_bytes(b"stary")
    klient = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404)))

    with pytest.raises(BladPobierania):
        pobierz_z_wydania(tmp_path, klient=klient, czekaj=lambda s: None)

    assert (tmp_path / PLIKI[0]).read_bytes() == b"stary"
