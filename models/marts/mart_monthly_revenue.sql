-- Indicador executivo: receita mensal, ticket médio e crescimento MoM.
with monthly as (
    select
        order_month,
        count(*)                    as orders,
        count(distinct customer_id) as active_customers,
        sum(order_total)            as revenue
    from {{ ref('fct_orders') }}
    where is_revenue
    group by order_month
)
select
    order_month,
    orders,
    active_customers,
    round(revenue, 2)          as revenue,
    round(revenue / orders, 2) as avg_ticket,
    round(
        (revenue - lag(revenue) over (order by order_month))
        / nullif(lag(revenue) over (order by order_month), 0) * 100
    , 2)                       as revenue_mom_pct
from monthly
order by order_month
