CREATE TABLE employees (
    emp_id INT PRIMARY KEY,
    name TEXT NOT NULL,
    department TEXT,
    salary INT,
    rating FLOAT,
    active BOOL
);

INSERT INTO employees VALUES
    (101, 'Asha', 'AI', 85000, 4.8, TRUE),
    (102, 'Rohan', 'Systems', 72000, 4.2, TRUE),
    (103, 'Meera', 'AI', 92000, 4.9, TRUE),
    (104, 'Kabir', 'Data', 68000, 4.0, FALSE),
    (105, 'Diya', 'Systems', 78000, 4.5, TRUE),
    (106, 'Arjun', 'Data', 71000, 4.1, TRUE);

EXPLAIN SELECT * FROM employees;
SELECT * FROM employees;

EXPLAIN SELECT name, department FROM employees WHERE department != 'AI';

EXPLAIN SELECT name FROM employees WHERE emp_id = 102;
SELECT name FROM employees WHERE emp_id = 102;
EXPLAIN SELECT name FROM employees WHERE emp_id = 102;

CREATE INDEX idx_employee_department ON employees (department) USING HASH;
CREATE INDEX idx_employee_salary ON employees (salary) USING BTREE;

EXPLAIN SELECT name, salary FROM employees WHERE department = 'AI';
SELECT name, salary FROM employees WHERE department = 'AI';

EXPLAIN SELECT name, salary FROM employees WHERE salary >= 78000;
SELECT name, salary FROM employees WHERE salary >= 78000;

BEGIN;
UPDATE employees SET salary = 50000 WHERE emp_id = 101;
SELECT emp_id, name, salary FROM employees WHERE emp_id = 101;
ROLLBACK;
SELECT emp_id, name, salary FROM employees WHERE emp_id = 101;

BEGIN;
UPDATE employees SET salary = 88000 WHERE emp_id = 101;
COMMIT;
SELECT emp_id, name, salary FROM employees WHERE emp_id = 101;

--delete and roll back
CREATE TABLE archive_records (
    record_id INT PRIMARY KEY,
    note TEXT NOT NULL
);
INSERT INTO archive_records VALUES
    (1, 'keep one'),
    (2, 'keep two'),
    (3, 'remove three'),
    (4, 'remove four');

BEGIN;
DELETE FROM archive_records WHERE record_id >= 3;
SELECT * FROM archive_records;
ROLLBACK;
SELECT * FROM archive_records;

DELETE FROM archive_records WHERE record_id >= 3;
SELECT * FROM archive_records;
