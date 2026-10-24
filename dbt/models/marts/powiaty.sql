-- Dostepnosc paczkomatow w kazdym z 380 powiatow. Ludnosc skalibrowana do GUS (patrz heksagony.sql).
with powiaty as (
    select
        powiat_id,
        any_value(powiat)                       as powiat,
        any_value(wojewodztwo)                  as wojewodztwo,
        sum(ludnosc)                            as ludnosc,
        sum(ludnosc_500m)                       as ludnosc_500m,
        sum(ludnosc_1km)                        as ludnosc_1km,
        sum(inpost)                         as paczkomaty,
        sum(inpost_w_budowie)               as paczkomaty_w_budowie,
        sum(automaty_konkurencji)               as automaty_konkurencji,
        any_value(wspolczynnik_kalibracji)      as wspolczynnik_kalibracji,
        sum(ludnosc) filter (where typ_zabudowy in ('Miasta', 'Małe miasta i osiedla')) as ludnosc_miejska
    from {{ ref('heksagony') }}
    where powiat_id is not null
    group by powiat_id
)
select
    powiat_id,
    powiat,
    wojewodztwo,
    -- 10 nazw powtarza sie w roznych wojewodztwach (np. powiat brzeski), wtedy dopisujemy wojewodztwo
    case when count(*) over (partition by powiat) > 1 then powiat || ' (' || wojewodztwo || ')' else powiat end
                                                            as nazwa,
    ludnosc,
    ludnosc_500m / ludnosc                                  as udzial_500m,
    ludnosc_1km / ludnosc                                   as udzial_1km,
    ludnosc - ludnosc_1km                                   as ludnosc_ponad_1km,
    coalesce(ludnosc_miejska, 0) / ludnosc                  as udzial_miejski,
    paczkomaty,
    paczkomaty_w_budowie,
    automaty_konkurencji,
    paczkomaty / ludnosc * 10000                            as paczkomaty_na_10_tys,
    wspolczynnik_kalibracji,
    rank() over (order by ludnosc_500m / ludnosc desc)      as miejsce_w_kraju
from powiaty
