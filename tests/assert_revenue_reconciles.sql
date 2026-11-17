-- Reconciliação: soma da receita mensal (mart) deve bater com a soma na fato.
select *
from (
    select
        (select sum(revenue) from {{ ref('mart_monthly_revenue') }})             as mart_total,
        (select sum(order_total) from {{ ref('fct_orders') }} where is_revenue) as fact_total
)
where abs(mart_total - fact_total) > 0.01
