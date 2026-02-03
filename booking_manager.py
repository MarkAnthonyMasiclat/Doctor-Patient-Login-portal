from datetime import date, datetime

class BookingManager:
    # The BookingManager handles all appointment logic and validation between the UI layer and the DatabaseManager.
    # AI Assistance: Documentation structure and minor logic optimisation
    # Team Member Contribution: Mark Anthony Masiclat
    # Fixed valid appointment times
    VALID_TIMES = ["09:00", "11:00", "13:00", "15:00"]

    def __init__(self, db_manager):
        # The constructor here is using dependency injection.
        # This receives DatabaseManager instance.
        self.db = db_manager  

    def _parse_date(self, d):
        # Converts string to date object if it is needed.
        return datetime.strptime(d, "%Y-%m-%d").date() if isinstance(d, str) else d

    def _date_str(self, d):
        # Converts date object to formatted string.
        return self._parse_date(d).strftime("%Y-%m-%d")

    def _is_weekday(self, d: date) -> bool:
        # Returns True if date is Monday–Friday.
        return d.weekday() <= 4  

    def _validate_date(self, d: date):
        # Ensures that the entered date is not in the past and is a only weekday.

        today = date.today()
        if d < today:
            return False, "Cannot book a past date."
        if not self._is_weekday(d):
            return False, "Appointments are Monday–Friday only."
        return True, ""

    def get_doctor_for_date(self, d):
        # Automatically assigns doctors on alternating weeks.
        dd = self._parse_date(d)
        week = dd.isocalendar().week
        return "D01" if week % 2 == 1 else "D02"

    def get_available_slots(self, d):
        # Returns list of available time slots based on current bookings.
        dd = self._parse_date(d)
        ok, _ = self._validate_date(dd)
        if not ok:
            return []

        doctor = self.get_doctor_for_date(dd)
        dstr = self._date_str(dd)
        active = self.db.get_active_bookings_for_date(doctor, dstr)
        taken = {b.time_slot for b in active if b.is_active == 1}

        return [t for t in self.VALID_TIMES if t not in taken]

    def book_appointment(self, patient_id, d, time_slot):
        # Creates a new validated booking.
        patient = self.db.get_patient_by_id(patient_id)
        if not patient:
            return "Invalid patient ID."

        dd = self._parse_date(d)
        ok, msg = self._validate_date(dd)
        if not ok:
            return msg

        if time_slot not in self.VALID_TIMES:
            return "Invalid time slot."

        available = self.get_available_slots(dd)
        if time_slot not in available:
            return "Selected time slot is unavailable."

        doctor = self.get_doctor_for_date(dd)
        dstr = self._date_str(dd)

        self.db.create_booking(patient_id, doctor, dstr, time_slot)

        if patient.needs_checkup == 1:
            self.db.set_patient_needs_checkup(patient_id, 0)

        return f"Booking confirmed for {dstr} at {time_slot}."

    def cancel_appointment(self, booking_id):
        # Cancels an appointment.
        self.db.cancel_booking(booking_id)
        return "Appointment cancelled successfully."
    
    def reschedule_appointment(self, booking_id, new_date, new_time):
        # Updates an existing appointment date and time.
        dd = self._parse_date(new_date)
        dstr = self._date_str(dd)
        conn = self.db._connect()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE Booking
            SET appointment_date=?, time_slot=?
            WHERE booking_id=?
        """, (dstr, new_time, booking_id))
        conn.commit()
        conn.close()

        return "Appointment rescheduled."