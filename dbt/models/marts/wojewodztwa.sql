-- 16 wojewodztw. paczkomaty_wg_api: liczba z pola "province" w API (ostatni zrzut) do kontroli jakosci;
-- glowna liczba "paczkomaty" pochodzi ze wspolrzednych, wiec oba zrodla powinny byc bardzo bliskie.
with z_heksagonow as (
    select
        wojewodztwo,
        sum(ludnosc)                as ludnosc,
        sum(ludnosc_500m)           as ludnosc_500m,
        sum(ludnosc_1km)            as ludnosc_1km,
        sum(inpost)             as paczkomaty,
        sum(inpost_w_budowie)   as paczkomaty_w_budowie,
        sum(automaty_konkurencji)   as automaty_konkurencji
    from {{ ref('heksagony') }}
    where wojewodztwo is not null
    group by wojewodztwo
),
api as (
    select wojewodztwo, sum(paczkomaty) as paczkomaty_wg_api
    from {{ ref('stg_stan_dzienny') }}
    where status = 'Operating' and data = (select max(data) from {{ ref('stg_stan_dzienny') }})
    group by wojewodztwo
)
select
    w.wojewodztwo,
    w.ludnosc,
    w.ludnosc_500m / w.ludnosc                              as udzial_500m,
    w.ludnosc_1km / w.ludnosc                               as udzial_1km,
    w.ludnosc - w.ludnosc_1km                               as ludnosc_ponad_1km,
    w.paczkomaty,
    w.paczkomaty_w_budowie,
    w.automaty_konkurencji,
    w.paczkomaty / w.ludnosc * 10000                        as paczkomaty_na_10_tys,
    a.paczkomaty_wg_api,
    rank() over (order by w.ludnosc_500m / w.ludnosc desc) as miejsce_w_kraju
from z_heksagonow as w
left join api as a using (wojewodztwo)
