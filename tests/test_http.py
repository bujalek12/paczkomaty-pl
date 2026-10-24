"""Testy pobierania z ponawianiem."""

import httpx
import pytest

from paczkomaty.http import BladPobierania, pobierz


def klient(obsluga) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(obsluga))


def test_ponawia_po_bledzie_serwera():
    proby = []

    def obsluga(zadanie):
        proby.append(1)
        return httpx.Response(503) if len(proby) < 3 else httpx.Response(200, json={"ok": True})

    odp = pobierz(klient(obsluga), "https://x.test/a", czekaj=lambda s: None)

    assert odp.json() == {"ok": True}
    assert len(proby) == 3


def test_nie_ponawia_404():
    proby = []

    def obsluga(zadanie):
        proby.append(1)
        return httpx.Response(404)

    with pytest.raises(BladPobierania):
        pobierz(klient(obsluga), "https://x.test/a", czekaj=lambda s: None)
    assert len(proby) == 1


def test_wysyla_post_z_danymi():
    odebrane = {}

    def obsluga(zadanie):
        odebrane["metoda"] = zadanie.method
        odebrane["cialo"] = zadanie.content.decode()
        return httpx.Response(200, json={})

    pobierz(klient(obsluga), "https://x.test/a", metoda="POST", dane={"data": "[out:json];"}, czekaj=lambda s: None)

    assert odebrane["metoda"] == "POST"
    assert "data=" in odebrane["cialo"]
