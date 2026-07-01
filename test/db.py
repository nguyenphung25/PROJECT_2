import sqlite3
from datetime import datetime

DB_NAME = "parking.db"


def get_conn():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parking_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_text TEXT NOT NULL,
            image_in TEXT,
            image_out TEXT,
            time_in TEXT NOT NULL,
            time_out TEXT,
            status TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def save_vehicle_in(plate_text, image_in):
    conn = get_conn()
    cursor = conn.cursor()

    time_in = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO parking_logs 
        (plate_text, image_in, time_in, status)
        VALUES (?, ?, ?, ?)
    """, (plate_text, image_in, time_in, "IN"))

    conn.commit()
    conn.close()


def find_vehicle_inside(plate_text):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, plate_text, time_in
        FROM parking_logs
        WHERE plate_text = ? AND status = 'IN'
        ORDER BY id DESC
        LIMIT 1
    """, (plate_text,))

    result = cursor.fetchone()

    conn.close()
    return result


def save_vehicle_out(plate_text, image_out):
    vehicle = find_vehicle_inside(plate_text)

    if vehicle is None:
        return False

    vehicle_id = vehicle[0]
    time_out = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE parking_logs
        SET image_out = ?, time_out = ?, status = ?
        WHERE id = ?
    """, (image_out, time_out, "OUT", vehicle_id))

    conn.commit()
    conn.close()

    return True