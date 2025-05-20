SELECT *
FROM employees
WHERE department_id = 200;

SELECT *
FROM transactions t
JOIN users u ON t.user_id = u.id
WHERE t.transaction_date BETWEEN '2023-01-01' AND '2023-12-31';

SELECT DISTINCT c.customer_name
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id;

SELECT DISTINCT s.store_name, p.product_name
FROM stores s
JOIN sales sa ON s.store_id = sa.store_id
JOIN products p ON sa.product_id = p.product_id
JOIN promotions pr ON pr.promo_id = sa.promo_id;

SELECT order_id
FROM orders
WHERE MONTH(order_date) = 12;

SELECT invoice_id, total_amount
FROM invoices
WHERE DATE(created_at) = '2024-03-15'
  AND HOUR(created_at) = 17;

SELECT user_id, email
FROM users
WHERE email LIKE '%@mydomain.com';

SELECT cust_id, notes
FROM customer_notes
WHERE notes LIKE '%urgent request';

SELECT p.product_id,
       (SELECT SUM(quantity)
        FROM order_items oi
        WHERE oi.product_id = p.product_id) AS total_qty
FROM products p;

SELECT t.ticket_id,
       (SELECT COUNT(*)
        FROM ticket_comments tc
        WHERE tc.ticket_id = t.ticket_id
          AND tc.created_at > t.last_updated) AS recent_comments,
       (SELECT AVG(rating)
        FROM ticket_feedback tf
        WHERE tf.ticket_id = t.ticket_id) AS avg_rating
FROM tickets t;

SELECT category_id, COUNT(*)
FROM products
GROUP BY category_id
HAVING category_id = 5;

SELECT region, SUM(total_sales)
FROM quarterly_sales
GROUP BY region
HAVING region IN ('North', 'East');

SELECT *
FROM events
WHERE event_type = 'Meeting'
   OR event_type = 'Webinar'
   OR event_type = 'Workshop';

SELECT t.task_name, t.due_date
FROM tasks t
WHERE t.priority = 'High'
   OR t.assigned_to = 'John'
   OR t.status = 'On Hold'
   OR t.category = 'Research';

SELECT a.author_name, b.book_title
FROM authors a
JOIN books b ON a.author_id = b.author_id;

SELECT c.customer_name, o.order_date, p.payment_method
FROM customers c
JOIN orders o ON c.id = o.customer_id
JOIN payments p ON o.id = p.order_id;

SELECT DISTINCT department_id, AVG(salary)
FROM employees
GROUP BY department_id;

SELECT DISTINCT d.division_name, SUM(e.salary)
FROM divisions d
JOIN employees e ON d.division_id = e.division_id
GROUP BY d.division_name;

SELECT *
FROM employee_records
WHERE employee_id = '12345';

SELECT t.ticket_id, t.opened_at
FROM tickets t
WHERE t.ticket_id = '784'
  AND t.opened_at < '2025-01-01';

SELECT user_id
FROM users
WHERE UPPER(username) = 'ADMIN';

SELECT sale_id, total
FROM sales
WHERE ABS(discount) > 10
  AND LOWER(payment_type) = 'credit';

SELECT *
FROM projects
WHERE project_id IN (101, 102, 103, 104, 105);

SELECT o.order_id, o.total
FROM orders o
WHERE o.order_id IN (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16);

SELECT *
FROM (SELECT customer_id FROM orders WHERE total_amount > 100) t;

SELECT *
FROM (
  SELECT user_id, AVG(score) AS avg_score
  FROM (
    SELECT user_id, score
    FROM user_scores
    WHERE date_scored > '2023-01-01'
  ) sub1
  GROUP BY user_id
) sub2
WHERE avg_score > 75;

SELECT e.employee_id, d.department_name
FROM employees e, departments d;

SELECT p.product_name, s.supplier_name
FROM products p, suppliers s, warehouses w;

SELECT UPPER(first_name), REPLACE(last_name, 'x', 'y')
FROM staff;

SELECT SUBSTR(CAST(o.total_amount * 100 AS VARCHAR(50)), 1, 5),
       CONCAT(LEFT(c.customer_name, 3), RIGHT(c.customer_name, 2))
FROM orders o
JOIN customers c ON o.customer_id = c.id;

SELECT order_id
FROM orders
HAVING order_id < 100;

SELECT customer_id
FROM customers
HAVING customer_id IN (201, 202, 203);

SELECT product_name
FROM inventory
WHERE category = 'Books'
   OR location = 'Aisle 5';

SELECT s.student_name, s.grade_level
FROM students s
WHERE s.city = 'New York'
   OR s.homeroom_teacher = 'Ms. Green'
   OR s.elective_subject = 'Art';

SELECT store_id, SUM(sales_amount) AS total_sales
FROM store_sales
GROUP BY store_id
HAVING SUM(sales_amount) > 5000;

SELECT campaign_id, COUNT(*) AS click_count
FROM ad_clicks
GROUP BY campaign_id
HAVING COUNT(*) > 10000;

SELECT *
INTO #temp_customers
FROM customers
WHERE status = 'ACTIVE';

SELECT *
INTO #latest_events
FROM event_logs
WHERE event_time > '2024-01-01';

SELECT *
INTO #filtered_events
FROM #latest_events
WHERE user_id IS NOT NULL;

SELECT transaction_id, amount
FROM transactions
WHERE transaction_date BETWEEN '2023-01-01' AND '2023-01-31';

SELECT *
FROM audit_logs
WHERE log_timestamp >= '2025-01-01 00:00:00'
  AND log_timestamp <= '2025-02-01 23:59:59'
  AND user_action = 'LOGIN';