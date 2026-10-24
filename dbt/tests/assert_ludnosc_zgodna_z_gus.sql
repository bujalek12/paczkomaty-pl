-- Po kalibracji suma mieszkancow kraju = suma z GUS (z dokladnoscia do zaokraglen).
select
    (select sum(ludnosc) from {{ ref('powiaty') }})          as po_kalibracji,
    (select sum(ludnosc_gus) from {{ ref('stg_ludnosc_gus') }}) as gus
where abs(po_kalibracji - gus) > 10
