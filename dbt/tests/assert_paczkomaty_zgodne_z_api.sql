-- Kontrola jakosci danych: liczba dzialajacych paczkomatow w wojewodztwie policzona ze wspolrzednych
-- i z pola "province" w API nie powinna sie roznic o wiecej niz 3%. Wieksza roznica = blad w granicach
-- albo w danych API. Ostrzezenie, nie blad: zrzut i agregaty moga byc z roznych dni.
{{ config(severity='warn') }}
select wojewodztwo, paczkomaty, paczkomaty_wg_api
from {{ ref('wojewodztwa') }}
where paczkomaty_wg_api is null or abs(paczkomaty - paczkomaty_wg_api) > 0.03 * paczkomaty_wg_api
