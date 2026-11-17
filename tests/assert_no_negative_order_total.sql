-- Falha se existir pedido com total negativo.
select order_id, order_total from {{ ref('fct_orders') }} where order_total < 0
