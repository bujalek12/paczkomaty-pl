-- Agregacja nie gubi ludzi: suma w powiatach = suma w szesciokatach z przypisanym powiatem,
-- a ludnosc bez powiatu (szesciokaty daleko od granic) to mniej niz 0,01% kraju.
with s as (
    select
        (select sum(ludnosc) from {{ ref('heksagony') }})                               as wszystkie,
        (select sum(ludnosc) from {{ ref('heksagony') }} where powiat_id is null)      as bez_powiatu,
        (select sum(ludnosc) from {{ ref('powiaty') }})                                 as w_powiatach,
        (select sum(ludnosc) from {{ ref('wojewodztwa') }})                             as w_wojewodztwach
)
select * from s
where abs(wszystkie - bez_powiatu - w_powiatach) > 1
   or abs(w_powiatach - w_wojewodztwach) > 1
   or bez_powiatu > 0.0001 * wszystkie
