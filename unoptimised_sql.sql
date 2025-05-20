SELECT *
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.order_date >= '2023-01-01';

SELECT DISTINCT c.customer_name, o.order_id
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
JOIN order_items i ON o.order_id = i.order_id
WHERE i.product_id IN (101, 102, 103);

SELECT c.customer_id, c.email
FROM customers c
WHERE c.email LIKE '%@example.com';

SELECT o.order_id, o.customer_id
FROM orders o
WHERE o.order_id IN (
    SELECT order_id 
    FROM order_items
    WHERE quantity > 5
);

SELECT order_id, product_id
FROM order_items
WHERE product_id IN (1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008);

SELECT *
FROM orders
WHERE YEAR(order_date) = 2023;

SELECT c.customer_name, o.order_id, o.order_date, i.product_id
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
JOIN order_items i ON o.order_id = i.order_id;

SELECT c.customer_name,
       COUNT(o.order_id) AS total_orders
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_name
HAVING COUNT(o.order_id) > 5; 

SELECT c.customer_name,
       (SELECT COUNT(*) FROM orders o WHERE o.customer_id = c.customer_id) AS total_orders,
       (SELECT SUM(total_amount) FROM orders o WHERE o.customer_id = c.customer_id) AS total_spent
FROM customers c;

SELECT DISTINCT
       o.customer_id,
       COUNT(o.order_id) AS total_orders
FROM orders o
GROUP BY o.customer_id;

SELECT *
FROM (
    SELECT *
    FROM customers
    WHERE customer_id IN (
        SELECT customer_id
        FROM orders
        WHERE order_date BETWEEN '2023-01-01' AND '2023-02-01'
    )
) c
WHERE c.customer_name LIKE '%Inc%';
