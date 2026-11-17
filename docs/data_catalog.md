# 📚 Catálogo de Dados

_Gerado automaticamente por `src/ai_docs.py`._

## `staging.stg_customers`

Clientes limpos e deduplicados. 1 linha por cliente.

| Coluna | Tipo | Descrição |
|---|---|---|
| `customer_id` | INTEGER | Chave primária do cliente. |
| `customer_name` | VARCHAR | — |
| `email` | VARCHAR | E-mail em minúsculas e sem espaços. |
| `state` | VARCHAR | UF em maiúsculas; 'NA' quando não informada. |
| `created_at` | DATE | — |

## `staging.stg_products`

Catálogo de produtos tipado. 1 linha por produto.

| Coluna | Tipo | Descrição |
|---|---|---|
| `product_id` | INTEGER | Chave primária do produto. |
| `product_name` | VARCHAR | — |
| `category` | VARCHAR | — |
| `list_price` | DECIMAL(12,2) | Preço de tabela em BRL. |

## `staging.stg_orders`

Pedidos deduplicados com status padronizado.

| Coluna | Tipo | Descrição |
|---|---|---|
| `order_id` | INTEGER | Chave primária do pedido. |
| `customer_id` | INTEGER | — |
| `order_date` | DATE | — |
| `status` | VARCHAR | Status normalizado do pedido. |

## `staging.stg_order_items`

Itens de pedido válidos (quantidade > 0).

| Coluna | Tipo | Descrição |
|---|---|---|
| `order_id` | INTEGER | Pedido ao qual o item pertence. |
| `product_id` | INTEGER | — |
| `quantity` | INTEGER | — |
| `unit_price` | DECIMAL(12,2) | — |
| `line_total` | DECIMAL(18,2) | quantity * unit_price. |

## `marts.fct_orders`

Fato de pedidos. 1 linha por pedido, com total e flag de receita.

| Coluna | Tipo | Descrição |
|---|---|---|
| `order_id` | INTEGER | Chave primária do pedido. |
| `customer_id` | INTEGER | Chave estrangeira para dim_customers. |
| `order_date` | DATE | — |
| `order_month` | DATE | — |
| `status` | VARCHAR | — |
| `item_lines` | BIGINT | — |
| `items_qty` | HUGEINT | — |
| `order_total` | DECIMAL(38,2) | Soma das linhas do pedido (BRL). |
| `is_revenue` | BOOLEAN | TRUE se o pedido não foi cancelado. |

## `marts.dim_customers`

Dimensão de clientes com métricas de histórico de compra.

| Coluna | Tipo | Descrição |
|---|---|---|
| `customer_id` | INTEGER | Chave primária do cliente. |
| `customer_name` | VARCHAR | — |
| `email` | VARCHAR | — |
| `state` | VARCHAR | — |
| `created_at` | DATE | — |
| `total_orders` | BIGINT | — |
| `lifetime_revenue` | DECIMAL(38,2) | Receita acumulada do cliente (pedidos não cancelados). |
| `first_order_date` | DATE | — |
| `last_order_date` | DATE | — |

## `marts.mart_monthly_revenue`

Receita mensal, ticket médio e crescimento MoM. Fonte para dashboards executivos.

| Coluna | Tipo | Descrição |
|---|---|---|
| `order_month` | DATE | Primeiro dia do mês. |
| `orders` | BIGINT | — |
| `active_customers` | BIGINT | — |
| `revenue` | DECIMAL(38,2) | Receita do mês (BRL). |
| `avg_ticket` | DOUBLE | — |
| `revenue_mom_pct` | DOUBLE | Variação percentual da receita vs. mês anterior. |

## `marts.mart_category_performance`

Receita, pedidos e unidades por categoria de produto.

| Coluna | Tipo | Descrição |
|---|---|---|
| `category` | VARCHAR | Categoria do produto. |
| `orders` | BIGINT | — |
| `units_sold` | HUGEINT | — |
| `revenue` | DECIMAL(38,2) | — |

## `marts.mart_customer_rfm`

Segmentação RFM de clientes com pelo menos um pedido válido.

| Coluna | Tipo | Descrição |
|---|---|---|
| `customer_id` | INTEGER | Chave do cliente. |
| `recency_days` | BIGINT | — |
| `frequency` | BIGINT | — |
| `monetary` | DECIMAL(38,2) | — |
| `r_score` | BIGINT | — |
| `f_score` | BIGINT | — |
| `m_score` | BIGINT | — |
| `segment` | VARCHAR | Segmento de negócio derivado dos scores RFM. |
