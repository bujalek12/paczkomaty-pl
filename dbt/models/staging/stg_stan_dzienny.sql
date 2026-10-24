select data::date as data, wojewodztwo, status, paczkomaty::integer as paczkomaty
from {{ source('agregaty', 'stan_dzienny') }}
