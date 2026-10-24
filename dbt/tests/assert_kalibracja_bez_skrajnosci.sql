-- Ostrzezenie: powiaty, w ktorych Kontur rozni sie od GUS wiecej niz 2 razy. Zwykle to miasta, z ktorych
-- Kontur "wyprowadzil" mieszkancow do sasiedniego powiatu ziemskiego (np. Elblag, Wloclawek, Suwalki).
-- Kalibracja to naprawia, ale warto wiedziec, gdzie byla potrzebna.
{{ config(severity='warn') }}
select nazwa, ludnosc, wspolczynnik_kalibracji
from {{ ref('powiaty') }}
where wspolczynnik_kalibracji > 2 or wspolczynnik_kalibracji < 0.5
