import asyncio
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.core.user import User, RequestContext

QA_PAIRS = [
    (
        "How many patients do we have?",
        "SELECT COUNT(*) AS total_patients FROM patients"
    ),
    (
        "List all patients from Mumbai",
        "SELECT first_name, last_name, email, phone FROM patients WHERE city = 'Mumbai'"
    ),
    (
        "How many female patients are registered?",
        "SELECT COUNT(*) AS female_patients FROM patients WHERE gender = 'F'"
    ),
    (
        "Which city has the most patients?",
        "SELECT city, COUNT(*) AS patient_count FROM patients GROUP BY city ORDER BY patient_count DESC LIMIT 1"
    ),
    (
        "List patients who visited more than 3 times",
        (
            "SELECT p.first_name, p.last_name, COUNT(a.id) AS visit_count "
            "FROM patients p JOIN appointments a ON a.patient_id = p.id "
            "GROUP BY p.id HAVING visit_count > 3 ORDER BY visit_count DESC"
        )
    ),
    (
        "List all doctors and their specializations",
        "SELECT name, specialization, department FROM doctors ORDER BY specialization"
    ),
    (
        "Which doctor has the most appointments?",
        (
            "SELECT d.name, COUNT(a.id) AS appointment_count "
            "FROM doctors d JOIN appointments a ON a.doctor_id = d.id "
            "GROUP BY d.id ORDER BY appointment_count DESC LIMIT 1"
        )
    ),
    (
        "Show revenue by doctor",
        (
            "SELECT d.name, SUM(i.total_amount) AS total_revenue "
            "FROM invoices i "
            "JOIN appointments a ON a.patient_id = i.patient_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "GROUP BY d.name ORDER BY total_revenue DESC"
        )
    ),
    (
        "Show me appointments for last month",
        (
            "SELECT a.id, p.first_name, p.last_name, d.name AS doctor, "
            "a.appointment_date, a.status "
            "FROM appointments a "
            "JOIN patients p ON p.id = a.patient_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "WHERE strftime('%Y-%m', a.appointment_date) = "
            "strftime('%Y-%m', date('now', '-1 month')) "
            "ORDER BY a.appointment_date"
        )
    ),
    (
        "How many cancelled appointments last quarter?",
        (
            "SELECT COUNT(*) AS cancelled_count FROM appointments "
            "WHERE status = 'Cancelled' AND appointment_date >= date('now', '-3 months')"
        )
    ),
    (
        "Show monthly appointment count for the past 6 months",
        (
            "SELECT strftime('%Y-%m', appointment_date) AS month, COUNT(*) AS total "
            "FROM appointments WHERE appointment_date >= date('now', '-6 months') "
            "GROUP BY month ORDER BY month"
        )
    ),
    (
        "What is the total revenue?",
        "SELECT SUM(total_amount) AS total_revenue FROM invoices WHERE status = 'Paid'"
    ),
    (
        "Show unpaid invoices",
        (
            "SELECT i.id, p.first_name, p.last_name, i.total_amount, i.paid_amount, i.status "
            "FROM invoices i JOIN patients p ON p.id = i.patient_id "
            "WHERE i.status IN ('Pending', 'Overdue') ORDER BY i.invoice_date DESC"
        )
    ),
    (
        "Top 5 patients by spending",
        (
            "SELECT p.first_name, p.last_name, SUM(i.total_amount) AS total_spending "
            "FROM invoices i JOIN patients p ON p.id = i.patient_id "
            "GROUP BY p.id ORDER BY total_spending DESC LIMIT 5"
        )
    ),
    (
        "Show patient registration trend by month",
        (
            "SELECT strftime('%Y-%m', registered_date) AS month, COUNT(*) AS new_patients "
            "FROM patients GROUP BY month ORDER BY month"
        )
    ),
]


async def seed():
    memory = DemoAgentMemory(max_items=1000)

    default_user = User(
        id="seed@clinic.local",
        username="seed@clinic.local",
        email="seed@clinic.local",
        group_memberships=["admin", "user"],
    )

    try:
        context = RequestContext(user=default_user)
    except TypeError:
        context = RequestContext()
        context.user = default_user

    print(f"Seeding {len(QA_PAIRS)} Q&A pairs into DemoAgentMemory...")

    for i, (question, sql) in enumerate(QA_PAIRS, 1):
        await memory.save_tool_usage(
            question=question,
            tool_name="run_sql",
            args={"sql": sql},
            context=context,
            success=True,
        )
        print(f"  [{i:02d}] {question[:65]}...")

    print(f"\nDone. {len(QA_PAIRS)} pairs seeded.")

    try:
        results = await memory.search_similar_usage(
            question="patients",
            context=context,
            limit=5,
        )
        print(f"Verification search returned {len(results)} result(s).")
    except Exception as e:
        print(f"Verification search skipped: {e}")


if __name__ == "__main__":
    asyncio.run(seed())
