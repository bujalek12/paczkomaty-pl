-- Wlasny test generyczny: wartosci kolumny musza miescic sie w [min, max].
-- Lapie np. udzial w procentach (0-100) zamiast ulamka (0-1) albo ujemne liczby.
{% test w_zakresie(model, column_name, min, max) %}
select {{ column_name }}
from {{ model }}
where {{ column_name }} < {{ min }} or {{ column_name }} > {{ max }}
{% endtest %}
