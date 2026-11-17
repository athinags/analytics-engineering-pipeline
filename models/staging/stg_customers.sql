-- Staging: limpa e padroniza clientes. Granularidade: 1 linha por customer_id.
with cleaned as (
    select
        cast(customer_id as integer)                   as customer_id,
        trim(name)                                     as customer_name,
        lower(trim(email))                             as email,
        coalesce(nullif(upper(trim(state)), ''), 'NA') as state,
        cast(created_at as date)                       as created_at
    from {{ source('raw', 'customers') }}
),
deduplicated as (
    select *, row_number() over (partition by customer_id order by created_at desc) as rn
    from cleaned
)
select customer_id, customer_name, email, state, created_at
from deduplicated
where rn = 1
