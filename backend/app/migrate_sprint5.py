import sqlite3


def column_exists(
    cursor,
    table_name: str,
    column_name: str
) -> bool:

    cursor.execute(
        f"PRAGMA table_info({table_name})"
    )

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    return column_name in columns


def migrate():

    conn = sqlite3.connect("rfid.db")
    cursor = conn.cursor()

    if not column_exists(
        cursor,
        "print_jobs",
        "generated_file"
    ):
        cursor.execute(
            "ALTER TABLE print_jobs "
            "ADD COLUMN generated_file VARCHAR(255)"
        )

    if not column_exists(
        cursor,
        "print_jobs",
        "generated_at"
    ):
        cursor.execute(
            "ALTER TABLE print_jobs "
            "ADD COLUMN generated_at DATETIME"
        )

    conn.commit()
    conn.close()

    print("Migration Sprint 5 terminée")


if __name__ == "__main__":
    migrate()