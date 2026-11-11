select i.*, o.ordered_at
from {{ ref('order_items') }} i
join {{ ref('orders') }} o using (order_id)
