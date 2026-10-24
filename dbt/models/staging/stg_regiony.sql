select h3, powiat_id::integer as powiat_id, powiat, wojewodztwo
from {{ source('agregaty', 'regiony_heksagonow') }}
