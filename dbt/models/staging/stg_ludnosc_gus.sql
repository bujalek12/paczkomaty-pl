select wojewodztwo, powiat, ludnosc_gus::bigint as ludnosc_gus
from {{ source('agregaty', 'ludnosc_gus_powiaty') }}
