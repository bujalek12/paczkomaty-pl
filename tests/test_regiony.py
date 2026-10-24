"""Testy ujednolicania nazw wojewodztw z API."""

import pytest

from paczkomaty.regiony import WOJEWODZTWA, normalizuj_wojewodztwo


@pytest.mark.parametrize("nazwa, oczekiwane", [
    ("mazowieckie", "mazowieckie"),
    ("Wielkopolskie", "wielkopolskie"),
    ("malopolskie", "małopolskie"),
    (" Śląskie ", "śląskie"),
    ("x", "nieznane"),
    (None, "nieznane"),
])
def test_normalizuje_nazwy(nazwa, oczekiwane):
    assert normalizuj_wojewodztwo(nazwa) == oczekiwane


def test_szesnascie_wojewodztw():
    assert len(WOJEWODZTWA) == 16
