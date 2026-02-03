import sqlite3
from dataclasses import dataclass

#GENERAL COMMENTS - dates are stored as text and follow the format: YYYY-MM-DD
    #AI was generally used to ensure DRY (Do-Not-Repeat) programming was used as code was unnecessarily repeated at first

@dataclass

#This is a data model that represents a single patient from the Patient table in the SQL database
#Each field, e.g. 'patient_id', maps directly to a column in the databse

class Patient:
    patient_id: str
    first_name: str
    last_name: str
    date_of_birth: str
    needs_checkup: int

@dataclass

#This is a data model that represents an appointment booking
#Once again, each field maps to a column in the Booking table from the SQL database
#'is_active' is used to preserve booking history instead of just deleting the rows completely

class Booking:
    booking_id: int
    patient_id: str
    doctor_id: str
    appointment_date: str
    time_slot: str
    is_active: int

@dataclass

#This class represents a doctor from the Doctor table in the SQL
#the storing of 'date_of_birth' allows for age-based logic if needed in future

class Doctor:
    doctor_id: str
    last_name: str
    date_of_birth: str


class DatabaseManager:

    # This class handles all the interactions with the SQLite Database, keeping database logic and program logic seperate
    #this makes potential databse changes easier because it only needs to be done in a single place rather than different .py files

    def __init__(self, db_path="clinic.db"):
        self.db_path = db_path

    def _connect(self):

        #This creates & returns a new database connection and is a private method, being used in this class only
        #new connections are opened each operation in order to reduce risk of locked connections

        return sqlite3.connect(self.db_path)
    
    def get_patient_by_id(self, patient_id):

        #This gets the patient id 
        #this returns the patient object if it can be found and returns None if nothing matching exists

        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Patient WHERE patient_id=?", (patient_id,))
        row = cursor.fetchone()
        conn.close()
        return Patient(*row) if row else None

    def set_patient_needs_checkup(self, patient_id, flag):

        #Update the checkup status for a patient
        #the flag is used to trigger reminders, prioritise patients and identify overdue checkups

        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE Patient SET needs_checkup=? WHERE patient_id=?",
            (flag, patient_id)
        )
        conn.commit()
        conn.close()

    def get_doctor_by_id(self, doctor_id):

        #gets a doctor by their id
        #this is used to validate doctors existence before creating and/or managing bookings

        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Doctor WHERE doctor_id=?", (doctor_id,))
        row = cursor.fetchone()
        conn.close()
        return Doctor(*row) if row else None

    def create_booking(self, patient_id, doctor_id, date, time_slot):

        #creates a new booking for patients
        #mentioned before, bookings aren't completely removed to preserve history

        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Booking (patient_id, doctor_id, appointment_date, time_slot, is_active)
            VALUES (?, ?, ?, ?, 1)
        """, (patient_id, doctor_id, date, time_slot))
        conn.commit()
        conn.close()

    def cancel_booking(self, booking_id):

        #cancels booking by setting is_active to 0

        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("UPDATE Booking SET is_active=0 WHERE booking_id=?", (booking_id,))
        conn.commit()
        conn.close()

    def get_active_bookings_for_date(self, doctor_id, date):

        #get active bookings for doctors on a specified date
        #display doctor's schedule
        #prevent double booking

        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM Booking
            WHERE doctor_id=? AND appointment_date=? AND is_active=1
        """, (doctor_id, date))
        rows = cursor.fetchall()
        conn.close()
        return [Booking(*r) for r in rows]

    def get_future_active_bookings_for_doctor(self, doctor_id, from_date):

        #gets future bookings for doctors, starting from a specific date
        #most useful for dashboards, managing queues & bulk notifications

        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM Booking
            WHERE doctor_id=? AND appointment_date>=? AND is_active=1
        """, (doctor_id, from_date))
        rows = cursor.fetchall()
        conn.close()
        return [Booking(*r) for r in rows]

    def get_all_active_bookings(self):

        #Return ALL active bookings in the entire database.

        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Booking WHERE is_active=1")
        rows = cursor.fetchall()
        conn.close()
        return [Booking(*r) for r in rows]
