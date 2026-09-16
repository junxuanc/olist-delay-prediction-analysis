/*
Project: Olist E-commerce Order Delay Prediction
Purpose: SQL exploratory analysis & feature table construction
Dataset: Olist Brazilian e-commerce dataset (PostgreSQL)
*/
--how many order status and how many orders in each statu in orders list
select order_status,count(*) number from olist_orders_dataset 
group by order_status;
--------------------------------------------
--only maintain the delivered and drop the rest
--check the null of the delivered date
select * from olist_orders_dataset where 
(order_delivered_customer_date='' or order_estimated_delivery_date='')  
and order_status='delivered';
--------------------------------------------
--recognize whether delay or on time
select *, case when order_delivered_customer_date>order_estimated_delivery_date
then 1 else 0 end is_delay from olist_orders_dataset where 
order_delivered_customer_date!='' and order_estimated_delivery_date!=''  
and order_status='delivered';
--------------------------------------------
--calculate the number and the ratio of delay and not delay
select sum(a.is_delay) num_delay, sum(a.is_delay)::numeric/count(*) delay_ratio, 
count(*)-sum(a.is_delay) num_on_time, 1-(sum(a.is_delay)::numeric/count(*)) on_time_ratio from 
(select *, case when order_delivered_customer_date>order_estimated_delivery_date
then 1 else 0 end is_delay from olist_orders_dataset where 
order_delivered_customer_date!='' and order_estimated_delivery_date!=''  
and order_status='delivered')a;
--------------------------------------------
--avg/median/min/max of delivery interval
select is_delay, COUNT(*) order_count, AVG(delivery_interval) avg_delivery_interval,
PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY delivery_interval) median_delivery_interval,
MIN(delivery_interval) min_delivery_interval, MAX(delivery_interval) max_delivery_interval
FROM (select CASE WHEN order_delivered_customer_date::timestamp > order_estimated_delivery_date::timestamp 
THEN 1 ELSE 0 END AS is_delay,(order_delivered_customer_date::timestamp - order_purchase_timestamp::timestamp) AS delivery_interval
FROM olist_orders_dataset where order_delivered_customer_date!=''
AND order_estimated_delivery_date!='' AND order_status='delivered') sub
GROUP BY is_delay;
--------------------------------------------
--raw delivery interval, export into csv file 
select CASE WHEN order_delivered_customer_date::timestamp > order_estimated_delivery_date::timestamp THEN 1 ELSE 0 END is_delay,
(order_delivered_customer_date::timestamp - order_purchase_timestamp::timestamp) delivery_interval
FROM olist_orders_dataset where order_delivered_customer_date!=''
AND order_estimated_delivery_date!='' AND order_status='delivered';
--------------------------------------------
--ratio of delay per month, export into csv file
select to_char(order_purchase_timestamp::timestamp,'yyyy-mm') year_month, 
count(*) monthly_total_orders,
sum(a.is_delay) monthly_delay_orders,
sum(a.is_delay)::numeric/count(*) ratio_delay_monthly 
from 
(select *, case when order_delivered_customer_date>order_estimated_delivery_date
then 1 else 0 end is_delay from olist_orders_dataset where 
order_delivered_customer_date!='' and order_estimated_delivery_date!=''  
and order_status='delivered')a 
group by year_month order by year_month;
--------------------------------------------
-- create join_table,export into csv file
WITH order_base AS (
SELECT order_id, customer_id,order_purchase_timestamp::timestamp,
order_delivered_customer_date::timestamp,order_estimated_delivery_date::timestamp,
CASE WHEN order_delivered_customer_date::timestamp > order_estimated_delivery_date::timestamp 
THEN 1 ELSE 0 END is_delay 
FROM olist_orders_dataset
WHERE order_status='delivered' AND order_delivered_customer_date!='' 
AND order_estimated_delivery_date!=''),
order_item_agg as (
select order_id,count(*)item_count,count(distinct(product_id)) product_count,
sum(price) total_price, sum(freight_value) total_freight
from olist_order_items_dataset group by order_id),
product_agg as(
select a.order_id,sum(b.product_weight_g) total_weight,avg(b.product_length_cm) avg_length,
avg(b.product_height_cm) avg_height,avg(b.product_width_cm) avg_width,avg(b.product_photos_qty) avg_photos
from olist_order_items_dataset a
left join olist_products_dataset b
on a.product_id=b.product_id
group by a.order_id),
payment_agg as (
select order_id,MODE() WITHIN GROUP (ORDER BY payment_type) payment_type,
avg(payment_installments) avg_installments 
from olist_order_payments_dataset
group by order_id)
select 
d.*, c.customer_state, ia.item_count,ia.product_count,ia.total_price,ia.total_freight,
pa.total_weight,pa.avg_length,pa.avg_height,pa.avg_width,avg_photos,
pay.payment_type,pay.avg_installments
from order_base d left join olist_customers_dataset c 
on d.customer_id=c.customer_id 
left join order_item_agg ia
on d.order_id=ia.order_id
left join product_agg pa
on d.order_id=pa.order_id
left join payment_agg pay
on d.order_id=pay.order_id;



