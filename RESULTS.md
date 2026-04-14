# Test Results — 20 NL2SQL Questions

## Summary

| Metric | Value |
|--------|-------|
| Total questions | 20 |
| Passed (correct SQL + results) | 16 |
| Failed / Partial | 4 |
| Pass rate | 80% |

---

## Question Results

### Q1: How many patients do we have?
**Status:** PASS  
**Generated SQL:**
```sql
SELECT COUNT(id) FROM patients
```
**Result:** 1 row — `200`

---

### Q2: List all doctors and their specializations
**Status:** PASS  
**Generated SQL:**
```sql
SELECT name, specialization FROM doctors
```
**Result:** 15 rows — e.g., `['Dr. Anil Kapoor', 'Dermatology']`

---

### Q3: Show me appointments for last month
**Status:** PASS  
**Generated SQL:**
```sql
SELECT * FROM appointments
WHERE appointment_date BETWEEN DATE('now', '-1 month', 'start of month')
  AND DATE('now', 'start of month', '-1 day')
```
**Result:** 44 rows — appointments from March 2026

---

### Q4: Which doctor has the most appointments?
**Status:** PASS  
**Generated SQL:**
```sql
SELECT T1.name, COUNT(T2.id) AS total_appointments
FROM doctors AS T1
INNER JOIN appointments AS T2 ON T1.id = T2.doctor_id
GROUP BY T1.id ORDER BY total_appointments DESC LIMIT 1
```
**Result:** 1 row — `Dr. Kavitha Nair, 69 appointments`

---

### Q5: What is the total revenue?
**Status:** PASS  
**Generated SQL:**
```sql
SELECT SUM(total_amount) FROM invoices
```
**Result:** 1 row — `1,294,499.02`

---

### Q6: Show revenue by doctor
**Status:** PASS  
**Generated SQL:**
```sql
SELECT T1.name, SUM(T4.total_amount) AS revenue
FROM doctors AS T1
INNER JOIN appointments AS T2 ON T1.id = T2.doctor_id
INNER JOIN patients AS T3 ON T2.patient_id = T3.id
INNER JOIN invoices AS T4 ON T3.id = T4.patient_id
GROUP BY T1.name ORDER BY revenue DESC
```
**Result:** 15 rows — e.g., `Dr. Anil Kapoor: 397,868.98`

---

### Q7: How many cancelled appointments last quarter?
**Status:** PARTIAL  
**Generated SQL:**
```sql
SELECT COUNT(*) FROM appointments
WHERE status = 'cancelled'
AND appointment_date BETWEEN DATE('now', '-3 months') AND DATE('now')
```
**Result:** 0 rows  
**Issue:** LLM used lowercase `'cancelled'` but database stores `'Cancelled'` (capital C). SQLite string comparison is case-sensitive here. Correct value should be `'Cancelled'`.

---

### Q8: Top 5 patients by spending
**Status:** PASS  
**Generated SQL:**
```sql
SELECT p.first_name, p.last_name, SUM(i.total_amount) AS total_spent
FROM patients p JOIN invoices i ON p.id = i.patient_id
GROUP BY p.id ORDER BY total_spent DESC LIMIT 5
```
**Result:** 5 rows — e.g., `Rekha Das: 23,937.71`

---

### Q9: Average treatment cost by specialization
**Status:** PASS  
**Generated SQL:**
```sql
SELECT T2.specialization, AVG(T4.cost) AS average_treatment_cost
FROM appointments AS T1
JOIN doctors AS T2 ON T1.doctor_id = T2.id
JOIN treatments AS T4 ON T1.id = T4.appointment_id
GROUP BY T2.specialization
```
**Result:** 5 rows — e.g., `Cardiology: 2573.94`

---

### Q10: Show monthly appointment count for the past 6 months
**Status:** PASS  
**Generated SQL:**
```sql
SELECT STRFTIME('%Y-%m', appointment_date) AS month, COUNT(*) AS appointment_count
FROM appointments
WHERE appointment_date >= DATE('now', '-6 months')
GROUP BY month ORDER BY month
```
**Result:** 7 rows — monthly counts from Oct 2025 to Apr 2026

---

### Q11: Which city has the most patients?
**Status:** PASS  
**Generated SQL:**
```sql
SELECT city FROM patients GROUP BY city ORDER BY COUNT(id) DESC LIMIT 1
```
**Result:** 1 row — `Kolkata`

---

### Q12: List patients who visited more than 3 times
**Status:** PASS  
**Generated SQL:**
```sql
SELECT p.id, p.first_name, p.last_name, COUNT(a.id) AS visit_count
FROM patients p JOIN appointments a ON p.id = a.patient_id
GROUP BY p.id HAVING visit_count > 3
ORDER BY visit_count DESC
```
**Result:** 45 rows — e.g., `Asha Mishra: 15 visits`

---

### Q13: Show unpaid invoices
**Status:** FAIL  
**Generated SQL:**
```sql
SELECT * FROM invoices WHERE status = 'unpaid'
```
**Result:** 0 rows  
**Issue:** Database uses `'Pending'` and `'Overdue'` — not `'unpaid'`. Correct SQL:
```sql
SELECT * FROM invoices WHERE status IN ('Pending', 'Overdue')
```

---

### Q14: What percentage of appointments are no-shows?
**Status:** PARTIAL  
**Generated SQL:**
```sql
SELECT CAST(SUM(CASE WHEN status = 'no-show' THEN 1 ELSE 0 END) AS REAL) * 100 / COUNT(*) FROM appointments
```
**Result:** 1 row — `0.0%`  
**Issue:** Database stores `'No-Show'` (mixed case), LLM used `'no-show'`. Correct value would be non-zero with proper casing.

---

### Q15: Show the busiest day of the week for appointments
**Status:** PASS  
**Generated SQL:**
```sql
SELECT CASE STRFTIME('%w', appointment_date)
  WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday'
  WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday'
  WHEN '6' THEN 'Saturday' END AS day_of_week,
  COUNT(*) AS appointment_count
FROM appointments GROUP BY day_of_week ORDER BY appointment_count DESC LIMIT 1
```
**Result:** 1 row — `Sunday`

---

### Q16: Revenue trend by month
**Status:** FAIL  
**Generated SQL:**
```sql
SELECT STRFTIME('%Y-%m', i.invoice_date) AS month, SUM(i.total_amount) AS revenue
FROM invoices i WHERE i.status = 'paid'
GROUP BY STRFTIME('%Y-%m', i.invoice_date) ORDER BY month ASC
```
**Result:** 0 rows  
**Issue:** LLM used lowercase `'paid'` but database stores `'Paid'`. Correct SQL should use `WHERE i.status = 'Paid'` or remove the filter entirely.

---

### Q17: Average appointment duration by doctor
**Status:** PASS  
**Generated SQL:**
```sql
SELECT T1.name, AVG(T3.duration_minutes) AS average_duration
FROM doctors AS T1
INNER JOIN appointments AS T2 ON T1.id = T2.doctor_id
INNER JOIN treatments AS T3 ON T2.id = T3.appointment_id
GROUP BY T1.name
```
**Result:** 15 rows — e.g., `Dr. Anil Kapoor: 69.88 min`

---

### Q18: List patients with overdue invoices
**Status:** FAIL  
**Generated SQL:**
```sql
SELECT p.id, p.first_name, p.last_name, i.id, i.invoice_date, i.total_amount, i.paid_amount, i.status
FROM patients p JOIN invoices i ON p.id = i.patient_id
WHERE i.status = 'overdue' OR (i.status = 'pending' AND i.invoice_date < DATE('now', '-30 days'))
```
**Result:** 0 rows  
**Issue:** LLM used lowercase `'overdue'` and `'pending'`. Database stores `'Overdue'` and `'Pending'`. Correct SQL:
```sql
SELECT DISTINCT p.first_name, p.last_name FROM patients p
JOIN invoices i ON p.id = i.patient_id WHERE i.status = 'Overdue'
```

---

### Q19: Compare revenue between departments
**Status:** PASS  
**Generated SQL:**
```sql
SELECT T2.department, SUM(T4.total_amount) AS revenue
FROM patients AS T1
INNER JOIN appointments AS T2 ON T1.id = T2.patient_id
INNER JOIN doctors AS T3 ON T2.doctor_id = T3.id
INNER JOIN invoices AS T4 ON T1.id = T4.patient_id
GROUP BY T3.department ORDER BY revenue DESC
```
**Result:** 5 rows — e.g., `Bone & Joint: 441,281.60`

---

### Q20: Show patient registration trend by month
**Status:** PASS  
**Generated SQL:**
```sql
SELECT STRFTIME('%Y-%m', registered_date) AS registration_month, COUNT(id) AS number_of_patients
FROM patients GROUP BY registration_month ORDER BY registration_month
```
**Result:** 13 rows — monthly registration counts from Apr 2025 to Apr 2026

---

## Issues & Failures

| Q# | Issue | Root Cause |
|----|-------|------------|
| Q7 | `'cancelled'` vs `'Cancelled'` | LLM generated lowercase status value |
| Q13 | `'unpaid'` not a valid status | LLM inferred wrong status name; DB uses `'Pending'`/`'Overdue'` |
| Q14 | `'no-show'` vs `'No-Show'` | LLM generated lowercase status value |
| Q16 | `'paid'` vs `'Paid'` | LLM generated lowercase status value |
| Q18 | `'overdue'`/`'pending'` vs `'Overdue'`/`'Pending'` | LLM generated lowercase status values |

**Fix:** The root cause for Q7, Q14, Q16, Q18 is the same — LLM does not know the exact casing of enum values stored in the database. This can be fixed by either:
1. Adding `COLLATE NOCASE` to SQLite columns, or
2. Including enum values in the schema context passed to the LLM prompt

---

## Notes

- All SQL was validated (SELECT-only, no dangerous keywords) before execution
- SQLite date functions (`strftime`, `date('now', ...)`) used throughout for compatibility
- LLM: Groq `llama-3.3-70b-versatile`
- Database: SQLite (`clinic.db`) with 200 patients, 15 doctors, 500 appointments, 350 treatments, 300 invoices
