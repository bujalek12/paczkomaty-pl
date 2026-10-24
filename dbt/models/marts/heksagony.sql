-- Jeden wiersz na szesciokat res 8: ludnosc skalibrowana do GUS, automaty, region, typ zabudowy, klasa zasiegu.
--
-- Kalibracja: Kontur w kilku miastach (np. Elblag, Wloclawek, Suwalki) przesuwa czesc mieszkancow poza granice
-- miasta, a w sumie daje 41 mln zamiast 37 mln. Dlatego liczbe mieszkancow powiatu bierzemy z GUS,
-- a Kontur tylko rozklada ich w obrebie powiatu: kazdy szesciokat mnozymy przez GUS / Kontur swojego powiatu.
-- Udzial mieszkancow w zasiegu w samym szesciokacie sie nie zmienia, zmienia sie jego waga.
{% set progi = var('progi_gestosci') %}
with h as (
    select h.*, r.powiat_id, r.powiat, r.wojewodztwo
    from {{ ref('stg_heksagony') }} as h
    left join {{ ref('stg_regiony') }} as r using (h3)
),
wspolczynniki as (
    select k.powiat_id, g.ludnosc_gus / k.ludnosc_kontur as wspolczynnik
    from (
        select powiat_id, any_value(powiat) as powiat, any_value(wojewodztwo) as wojewodztwo,
               sum(ludnosc) as ludnosc_kontur
        from h where powiat_id is not null group by powiat_id
    ) as k
    left join {{ ref('stg_ludnosc_gus') }} as g using (wojewodztwo, powiat)
),
skalibrowane as (
    select
        h.* exclude (ludnosc, ludnosc_500m, ludnosc_1km),
        h.ludnosc                                           as ludnosc_kontur,
        -- szesciokaty bez powiatu (pojedyncze, za granica kraju) dostaja 0 mieszkancow
        h.ludnosc * coalesce(w.wspolczynnik, 0)             as ludnosc,
        h.ludnosc_500m * coalesce(w.wspolczynnik, 0)        as ludnosc_500m,
        h.ludnosc_1km * coalesce(w.wspolczynnik, 0)         as ludnosc_1km,
        w.wspolczynnik                                      as wspolczynnik_kalibracji
    from h
    left join wspolczynniki as w using (powiat_id)
)
select
    *,
    allegro_one_box + orlen_paczka + dpd + dhl + pocztex   as automaty_konkurencji,
    ludnosc / {{ var('powierzchnia_res8_km2') }}           as gestosc_km2,
    case
        when ludnosc / {{ var('powierzchnia_res8_km2') }} > {{ progi[2] }} then 'Miasta'
        when ludnosc / {{ var('powierzchnia_res8_km2') }} > {{ progi[1] }} then 'Małe miasta i osiedla'
        when ludnosc / {{ var('powierzchnia_res8_km2') }} > {{ progi[0] }} then 'Wieś i przedmieścia'
        when ludnosc > 0 then 'Zabudowa rozproszona'
        else 'Bez mieszkańców'
    end                                                     as typ_zabudowy,
    -- jak daleko do paczkomatu ma wiekszosc (co najmniej polowa) mieszkancow, jak klasa_zasiegu w widoki.py
    case
        when ludnosc = 0 then 'bez mieszkańców'
        when ludnosc_500m / ludnosc >= 0.5 then 'do 500 m'
        when ludnosc_1km / ludnosc >= 0.5 then 'do 1 km'
        else 'ponad 1 km'
    end                                                     as klasa_zasiegu
from skalibrowane
