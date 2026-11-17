-- Segmentação RFM (Recência, Frequência, Valor monetário).
-- A data de referência é a última data de pedido do dataset (resultado reproduzível).
with base as (
    select
        customer_id,
        max(order_date)  as last_order_date,
        count(*)         as frequency,
        sum(order_total) as monetary
    from {{ ref('fct_orders') }}
    where is_revenue
    group by customer_id
),
reference as (
    select max(order_date) as ref_date from {{ ref('fct_orders') }}
),
scored as (
    select
        b.*,
        date_diff('day', b.last_order_date, r.ref_date) as recency_days,
        ntile(4) over (order by b.last_order_date asc)  as r_score,  -- 4 = compra mais recente
        ntile(4) over (order by b.frequency asc)        as f_score,
        ntile(4) over (order by b.monetary asc)         as m_score
    from base b
    cross join reference r
)
select
    customer_id,
    recency_days,
    frequency,
    round(monetary, 2) as monetary,
    r_score, f_score, m_score,
    case
        when r_score >= 3 and f_score >= 3 then 'Champions'
        when r_score <= 2 and f_score >= 3 then 'At Risk'
        when r_score >= 3 and f_score <= 2 then 'Promising'
        else 'Hibernating'
    end as segment
from scored
