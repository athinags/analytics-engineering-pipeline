-- Staging: itens de pedido. Remove quantidades inválidas (<= 0) e calcula o total da linha.
select
    cast(order_id as integer)          as order_id,
    cast(product_id as integer)        as product_id,
    cast(quantity as integer)          as quantity,
    cast(unit_price as decimal(12, 2)) as unit_price,
    cast(quantity as integer) * cast(unit_price as decimal(12, 2)) as line_total
from {{ source('raw', 'order_items') }}
where cast(quantity as integer) > 0
