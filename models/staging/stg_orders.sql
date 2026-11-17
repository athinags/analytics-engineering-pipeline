-- Staging: pedidos sem duplicatas e com status padronizado.
-- 'cancelled' (UK) e 'canceled' (US) viram um único valor.
with cleaned as (
    select
        cast(order_id as integer)    as order_id,
        cast(customer_id as integer) as customer_id,
        cast(order_date as date)     as order_date,
        case
            when lower(trim(status)) in ('canceled', 'cancelled') then 'canceled'
            else lower(trim(status))
        end                          as status
    from {{ source('raw', 'orders') }}
),
deduplicated as (
    select *, row_number() over (partition by order_id order by order_date) as rn
    from cleaned
)
select order_id, customer_id, order_date, status
from deduplicated
where rn = 1
