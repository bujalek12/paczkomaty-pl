-- Mieszkancy "w zasiegu" to podzbior mieszkancow: wiecej niz ludnosc = blad w laczeniu albo liczeniu.
-- Margines 1e-6 na zaokraglenia (ludnosc res 8 dzielona na 7 dzieci res 9 i sumowana z powrotem).
{% test nie_wiecej_niz_ludnosc(model, column_name) %}
select h3, {{ column_name }}, ludnosc
from {{ model }}
where {{ column_name }} > ludnosc + 1e-6
{% endtest %}
