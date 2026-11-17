-- Reconciliação: receita por categoria deve bater com a receita total da fato.
select *
from (
    select
        (select sum(revenue) from {{ ref('mart_category_performance') }})       as category_total,
        (select sum(order_total) from {{ ref('fct_orders') }} where is_revenue) as fact_total
)
where abs(category_total - fact_total) > 0.01
