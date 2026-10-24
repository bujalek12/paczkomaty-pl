-- Ostrzezenie: powiaty z niepewnym rozkladem ludnosci (pary miasto + powiat ziemski, patrz powiaty.sql). Zwykle to miasta, z ktorych
-- Kontur "wyprowadzil" mieszkancow do sasiedniego powiatu ziemskiego (np. Elblag, Wloclawek, Suwalki).
-- Kalibracja naprawia sume, ale warto wiedziec, gdzie byla potrzebna (kolumna dane_niepewne).
{{ config(severity='warn') }}
select nazwa, ludnosc, wspolczynnik_kalibracji
from {{ ref('powiaty') }}
where dane_niepewne
