-- Fato de pedidos. Granularidade: 1 linha por pedido.
-- is_revenue = TRUE quando o pedido conta como receita (não cancelado).
with items as (
    select
        order_id,
        count(*)        as item_lines,
        sum(quantity)   as items_qty,
        sum(line_total) as order_total
    from {{ ref('stg_order_items') }}
    group by order_id
)
select
    o.order_id,
    o.customer_id,
    o.order_date,
    cast(date_trunc('month', o.order_date) as date) as order_month,
    o.status,
    coalesce(i.item_lines, 0)  as item_lines,
    coalesce(i.items_qty, 0)   as items_qty,
    coalesce(i.order_total, 0) as order_total,
    (o.status <> 'canceled')   as is_revenue
from {{ ref('stg_orders') }} o
left join items i on i.order_id = o.order_id
