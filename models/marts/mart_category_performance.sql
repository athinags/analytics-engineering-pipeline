-- Receita e volume por categoria de produto (apenas pedidos não cancelados).
select
    p.category,
    count(distinct i.order_id)  as orders,
    sum(i.quantity)             as units_sold,
    round(sum(i.line_total), 2) as revenue
from {{ ref('stg_order_items') }} i
join {{ ref('fct_orders') }}   o on o.order_id = i.order_id and o.is_revenue
join {{ ref('stg_products') }} p on p.product_id = i.product_id
group by p.category
order by revenue desc
