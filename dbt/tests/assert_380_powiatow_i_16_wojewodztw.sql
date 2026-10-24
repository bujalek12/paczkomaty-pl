-- Podzial administracyjny Polski: 380 powiatow (w tym 66 miast na prawach powiatu) i 16 wojewodztw.
select 'powiaty' as poziom, count(*) as liczba from {{ ref('powiaty') }} having count(*) <> 380
union all
select 'wojewodztwa', count(*) from {{ ref('wojewodztwa') }} having count(*) <> 16
