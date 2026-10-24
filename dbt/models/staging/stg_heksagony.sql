select
    h3,
    ludnosc,
    ludnosc_500m,
    ludnosc_1km,
    inpost::integer             as inpost,
    inpost_w_budowie::integer   as inpost_w_budowie,
    allegro_one_box::integer    as allegro_one_box,
    orlen_paczka::integer       as orlen_paczka,
    dpd::integer                as dpd,
    dhl::integer                as dhl,
    pocztex::integer            as pocztex,
    lat,
    lon
from {{ source('agregaty', 'heksagony_res8') }}
