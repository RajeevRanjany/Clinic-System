import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "clinic.db"

SCHEMA = """
DROP TABLE IF EXISTS invoices;
DROP TABLE IF EXISTS treatments;
DROP TABLE IF EXISTS appointments;
DROP TABLE IF EXISTS doctors;
DROP TABLE IF EXISTS patients;

CREATE TABLE patients (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL,
    email           TEXT,
    phone           TEXT,
    date_of_birth   DATE,
    gender          TEXT,
    city            TEXT,
    registered_date DATE
);

CREATE TABLE doctors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    specialization  TEXT,
    department      TEXT,
    phone           TEXT
);

CREATE TABLE appointments (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id       INTEGER REFERENCES patients(id),
    doctor_id        INTEGER REFERENCES doctors(id),
    appointment_date DATETIME,
    status           TEXT,
    notes            TEXT
);

CREATE TABLE treatments (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id   INTEGER REFERENCES appointments(id),
    treatment_name   TEXT,
    cost             REAL,
    duration_minutes INTEGER
);

CREATE TABLE invoices (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id   INTEGER REFERENCES patients(id),
    invoice_date DATE,
    total_amount REAL,
    paid_amount  REAL,
    status       TEXT
);
"""

FIRST_NAMES = [
    "Aarav", "Priya", "Rahul", "Sneha", "Vikram", "Ananya", "Rohan", "Kavya",
    "Arjun", "Divya", "Kiran", "Meera", "Suresh", "Pooja", "Amit", "Neha",
    "Rajesh", "Sunita", "Deepak", "Anjali", "Sanjay", "Rekha", "Manoj", "Geeta",
    "Arun", "Shweta", "Vinod", "Nisha", "Prakash", "Usha", "Ravi", "Lata",
    "Sunil", "Manju", "Ashok", "Seema", "Ramesh", "Poonam", "Dinesh", "Asha",
    "Harish", "Savita", "Naresh", "Kamla", "Girish", "Sudha", "Mahesh", "Radha",
    "Satish", "Pushpa"
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Singh", "Kumar", "Gupta", "Joshi", "Mehta",
    "Shah", "Rao", "Nair", "Iyer", "Reddy", "Pillai", "Bose", "Das",
    "Chatterjee", "Mukherjee", "Banerjee", "Ghosh", "Mishra", "Tiwari",
    "Pandey", "Dubey", "Yadav", "Chauhan", "Rajput", "Thakur", "Saxena", "Sinha"
]

CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai",
    "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Surat"
]

SPECIALIZATIONS = {
    "Dermatology": "Skin & Hair",
    "Cardiology": "Heart & Vascular",
    "Orthopedics": "Bone & Joint",
    "General": "General Medicine",
    "Pediatrics": "Child Health",
}

DOCTOR_NAMES = [
    ("Dr. Anil Kapoor", "Dermatology"),
    ("Dr. Sunita Rao", "Dermatology"),
    ("Dr. Pradeep Mehta", "Dermatology"),
    ("Dr. Kavitha Nair", "Cardiology"),
    ("Dr. Ramesh Iyer", "Cardiology"),
    ("Dr. Shalini Gupta", "Cardiology"),
    ("Dr. Vijay Sharma", "Orthopedics"),
    ("Dr. Meena Patel", "Orthopedics"),
    ("Dr. Suresh Verma", "Orthopedics"),
    ("Dr. Anita Singh", "General"),
    ("Dr. Rajiv Kumar", "General"),
    ("Dr. Deepa Joshi", "General"),
    ("Dr. Harish Reddy", "Pediatrics"),
    ("Dr. Pooja Shah", "Pediatrics"),
    ("Dr. Nikhil Das", "Pediatrics"),
]

TREATMENT_NAMES = {
    "Dermatology": ["Acne Treatment", "Skin Biopsy", "Laser Therapy", "Chemical Peel", "Mole Removal"],
    "Cardiology": ["ECG", "Echocardiogram", "Stress Test", "Angioplasty", "Holter Monitor"],
    "Orthopedics": ["X-Ray", "MRI Scan", "Physiotherapy", "Joint Injection", "Fracture Management"],
    "General": ["Blood Test", "Urine Analysis", "Vaccination", "General Checkup", "BP Monitoring"],
    "Pediatrics": ["Growth Assessment", "Vaccination", "Nebulization", "Allergy Test", "Nutrition Counseling"],
}

APPOINTMENT_NOTES = [
    "Patient reported mild discomfort.",
    "Follow-up required in 2 weeks.",
    "Prescribed medication for 5 days.",
    "No complications observed.",
    "Patient advised rest for 3 days.",
    None, None, None,
]

APPOINTMENT_STATUSES = ["Scheduled", "Completed", "Cancelled", "No-Show"]
INVOICE_STATUSES = ["Paid", "Pending", "Overdue"]


def random_date(start_days_ago: int, end_days_ago: int = 0) -> str:
    delta = random.randint(end_days_ago, start_days_ago)
    return (datetime.now() - timedelta(days=delta)).strftime("%Y-%m-%d")


def random_datetime(start_days_ago: int, end_days_ago: int = 0) -> str:
    delta = random.randint(end_days_ago, start_days_ago)
    hour = random.randint(8, 17)
    minute = random.choice([0, 15, 30, 45])
    dt = datetime.now() - timedelta(days=delta, hours=hour, minutes=minute)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def maybe_null(value, null_prob: float = 0.15):
    return None if random.random() < null_prob else value


def insert_doctors(cur):
    rows = []
    for name, spec in DOCTOR_NAMES:
        dept = SPECIALIZATIONS[spec]
        phone = maybe_null(f"+91-{random.randint(7000000000, 9999999999)}", 0.1)
        rows.append((name, spec, dept, phone))
    cur.executemany(
        "INSERT INTO doctors (name, specialization, department, phone) VALUES (?,?,?,?)",
        rows
    )
    return len(rows)


def insert_patients(cur, n: int = 200):
    rows = []
    used_emails = set()
    for _ in range(n):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)

        email = None
        if random.random() > 0.15:
            base = f"{first.lower()}.{last.lower()}{random.randint(1,999)}@example.com"
            while base in used_emails:
                base = f"{first.lower()}.{last.lower()}{random.randint(1,9999)}@example.com"
            used_emails.add(base)
            email = base

        phone = maybe_null(f"+91-{random.randint(7000000000, 9999999999)}", 0.1)
        dob = random_date(365 * 70, 365 * 18)
        gender = random.choice(["M", "F"])
        city = random.choice(CITIES)
        reg_date = random_date(365, 0)

        rows.append((first, last, email, phone, dob, gender, city, reg_date))

    cur.executemany(
        """INSERT INTO patients
           (first_name, last_name, email, phone, date_of_birth, gender, city, registered_date)
           VALUES (?,?,?,?,?,?,?,?)""",
        rows
    )
    return len(rows)


def insert_appointments(cur, n_patients: int, n_doctors: int, n: int = 500):
    heavy_patients = random.sample(range(1, n_patients + 1), k=int(n_patients * 0.2))
    light_patients = [i for i in range(1, n_patients + 1) if i not in heavy_patients]

    doctor_weights = []
    for i in range(1, n_doctors + 1):
        doctor_weights.append(3 if i <= 5 else 1)

    rows = []
    for _ in range(n):
        if random.random() < 0.6:
            patient_id = random.choice(heavy_patients)
        else:
            patient_id = random.choice(light_patients)

        doctor_id = random.choices(range(1, n_doctors + 1), weights=doctor_weights)[0]
        appt_dt = random_datetime(365, 0)
        status = random.choices(
            APPOINTMENT_STATUSES,
            weights=[10, 65, 15, 10]
        )[0]
        notes = maybe_null(random.choice(APPOINTMENT_NOTES), 0.3)

        rows.append((patient_id, doctor_id, appt_dt, status, notes))

    cur.executemany(
        """INSERT INTO appointments
           (patient_id, doctor_id, appointment_date, status, notes)
           VALUES (?,?,?,?,?)""",
        rows
    )
    return len(rows)


def insert_treatments(cur, n: int = 350):
    cur.execute("SELECT id, doctor_id FROM appointments WHERE status = 'Completed'")
    completed = cur.fetchall()

    if not completed:
        return 0

    cur.execute("SELECT id, specialization FROM doctors")
    doc_spec = {row[0]: row[1] for row in cur.fetchall()}

    rows = []
    for _ in range(n):
        appt_id, doctor_id = random.choice(completed)
        spec = doc_spec.get(doctor_id, "General")
        treatment = random.choice(TREATMENT_NAMES.get(spec, TREATMENT_NAMES["General"]))
        cost = round(random.uniform(50, 5000), 2)
        duration = random.randint(15, 120)
        rows.append((appt_id, treatment, cost, duration))

    cur.executemany(
        "INSERT INTO treatments (appointment_id, treatment_name, cost, duration_minutes) VALUES (?,?,?,?)",
        rows
    )
    return len(rows)


def insert_invoices(cur, n_patients: int, n: int = 300):
    rows = []
    patient_ids = random.choices(range(1, n_patients + 1), k=n)
    for pid in patient_ids:
        inv_date = random_date(365, 0)
        total = round(random.uniform(100, 8000), 2)
        status = random.choices(INVOICE_STATUSES, weights=[50, 30, 20])[0]
        paid = total if status == "Paid" else round(random.uniform(0, total * 0.5), 2)
        rows.append((pid, inv_date, total, paid, status))

    cur.executemany(
        "INSERT INTO invoices (patient_id, invoice_date, total_amount, paid_amount, status) VALUES (?,?,?,?,?)",
        rows
    )
    return len(rows)


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(SCHEMA)
    conn.commit()

    n_doctors = insert_doctors(cur)
    conn.commit()

    n_patients = insert_patients(cur, 200)
    conn.commit()

    n_appointments = insert_appointments(cur, n_patients, n_doctors, 500)
    conn.commit()

    n_treatments = insert_treatments(cur, 350)
    conn.commit()

    n_invoices = insert_invoices(cur, n_patients, 300)
    conn.commit()

    conn.close()

    print(f"Created {n_patients} patients, {n_doctors} doctors, "
          f"{n_appointments} appointments, {n_treatments} treatments, "
          f"{n_invoices} invoices.")
    print(f"Database saved to: {DB_PATH}")


if __name__ == "__main__":
    main()
