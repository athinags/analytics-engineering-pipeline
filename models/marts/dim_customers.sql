-- Dimensão de clientes enriquecida com métricas de histórico de compra.
with orders as (
    select
        customer_id,
        count(*)         as total_orders,
        sum(order_total) as lifetime_revenue,
        min(order_date)  as first_order_date,
        max(order_date)  as last_order_date
    from {{ ref('fct_orders') }}
    where is_revenue
    group by customer_id
)
select
    c.customer_id,
    c.customer_name,
    c.email,
    c.state,
    c.created_at,
    coalesce(o.total_orders, 0)     as total_orders,
    coalesce(o.lifetime_revenue, 0) as lifetime_revenue,
    o.first_order_date,
    o.last_order_date
from {{ ref('stg_customers') }} c
left join orders o on o.customer_id = c.customer_id
