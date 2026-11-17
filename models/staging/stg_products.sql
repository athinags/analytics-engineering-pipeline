-- Staging: produtos com tipos corretos. Granularidade: 1 linha por product_id.
select
    cast(product_id as integer)   as product_id,
    trim(name)                    as product_name,
    trim(category)                as category,
    cast(price as decimal(12, 2)) as list_price
from {{ source('raw', 'products') }}
