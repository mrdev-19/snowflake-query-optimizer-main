SELECT *
FROM orders;

SELECT DISTINCT o.order_id, c.customer_name
FROM orders o
JOIN order_items i ON o.order_id = i.order_id
JOIN customers c ON c.customer_id = o.customer_id;

SELECT customer_id, email
FROM customers
WHERE email LIKE '%@example.com';

SELECT 
    o.order_id,
    (SELECT COUNT(*) FROM order_items i WHERE i.order_id = o.order_id) AS item_count
FROM orders o;

SELECT order_id, product_id
FROM order_items
WHERE product_id = 1001
   OR product_id = 1002
   OR product_id = 1003
   OR product_id = 1004
   OR product_id = 1005;

SELECT *
FROM orders
WHERE YEAR(order_date) = 2023;

SELECT user_id
FROM users
WHERE LOWER(username) = 'johndoe';

SELECT *
FROM customers
WHERE phone_number = '1234567890';

SELECT c.customer_name, o.order_id, i.product_id
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items i ON o.order_id = i.order_id;

SELECT c.customer_id, COUNT(o.order_id) AS order_count
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id
HAVING c.customer_id > 1000;  -- This filter belongs in a WHERE

SELECT 
    (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.customer_id) AS total_orders,
    (SELECT SUM(total_amount) FROM orders o WHERE o.customer_id = c.customer_id) AS total_spent
FROM customers c;

SELECT DISTINCT
       o.customer_id,
       COUNT(o.order_id) AS total_orders
FROM orders o
GROUP BY o.customer_id;

SELECT *
FROM products
WHERE product_id IN (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12);

SELECT *
FROM (
  SELECT order_id, SUM(quantity) as total_quantity
  FROM (
    SELECT order_id, quantity
    FROM order_items
    WHERE quantity > 2
  ) sub1
  GROUP BY order_id
) sub2
WHERE total_quantity > 10;

SELECT o.order_id, c.customer_name
FROM orders o
CROSS JOIN customers c
WHERE o.order_id = 123; 

SELECT
    CONCAT(first_name, ' ', last_name) AS full_name,
    REPLACE(email, '.com', '.org') AS updated_email
FROM customers;

SELECT o.order_id
FROM (
    SELECT order_id
    FROM orders
    ORDER BY order_id
) o;

SELECT c.customer_id, o.*
FROM customers c
CROSS APPLY (
    SELECT *
    FROM orders o
    WHERE o.customer_id = c.customer_id
) o;

SELECT 
    customer_id,
    (SELECT COUNT(*) FROM orders WHERE order_status = 'NEW'   AND customer_id = c.customer_id) as new_count,
    (SELECT COUNT(*) FROM orders WHERE order_status = 'PAID'  AND customer_id = c.customer_id) as paid_count,
    (SELECT COUNT(*) FROM orders WHERE order_status = 'CANCELED' AND customer_id = c.customer_id) as canceled_count
FROM customers c;

SELECT c.customer_id
FROM customers c
WHERE EXISTS (
    SELECT 1 
    FROM orders o
    WHERE o.customer_id = c.customer_id
      AND o.total_amount > 500
);

SELECT *
FROM big_events
WHERE created_date BETWEEN '2023-01-01' AND '2023-02-01';
 
SELECT
    t1.col_a,
    t2.col_b
FROM table1 t1
CROSS JOIN table2 t2
WHERE t1.key = t2.key;

SELECT 
    line_price * quantity * (1 - discount/100) * (1 + tax_rate/100) AS final_line_item_cost
FROM order_items;

SELECT *
FROM events
WHERE event_timestamp > '2023-09-10 00:00:00';

