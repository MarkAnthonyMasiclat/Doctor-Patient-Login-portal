from datetime import date, datetime
import calendar
from nicegui import ui
from database_manager import DatabaseManager  # Conor's class: handles all patient, doctor, booking queries
from booking_manager import BookingManager  # Mark's class: encapsulates booking rules and constraints

# Create shared objects once and reuse them in all pages.
db = DatabaseManager()
bm = BookingManager(db)

# Simple global state for "logged in" user or doctor.
current_patient_id: str | None = None
current_doctor_id: str | None = None

# Business rule from Mark's booking logic, reused in main.py for UI.
VALID_TIMES = ["09:00", "11:00", "13:00", "15:00"]

# Helper to format dates consistently for the database and display.
def fmt_date(d: date) -> str:
    return d.strftime("%Y-%m-%d")

# Helper to get today's date as a string.
def today_str() -> str:
    return fmt_date(date.today())

# calling on Connor's database manager to get patient info.
def get_patient_name(pid: str) -> str:
    patient = db.get_patient_by_id(pid)
    if not patient:
        return pid
    return f"{patient.first_name} {patient.last_name}"

# Calling on Connor's database manager to get doctor info.
def get_doctor_display_name(did: str) -> str:
    doctor = db.get_doctor_by_id(did)
    if not doctor:
        return did
    return f"Dr {doctor.last_name}"

# Start of landing UI pages Ai helped on creating the Ui it was done by creating a visual landing page with images in photoshop and then converting it to code using nicegui components with Ai,
# afterwards it was manually moved around to centre as the ai built everything to be on the far left or right side. 
# The notifcations were added to give feedback to the user what is happening when they click buttons or try to login with wrong credentials these were added manually after the ai created the initial code.

@ui.page('/')
def index_page():
    with ui.row().classes('w-full h-screen items-center justify-center'):
        with ui.column().classes('items-center q-gutter-md'):
            ui.label('Doctor Appointment Notice').classes('text-h4 text-center')
            ui.label(
                'Patients can check if they need a follow up and book an appointment. '
                'Doctors can view and manage their schedule.'
            ).classes('text-body1 q-mx-xl text-center')

            ui.label('Select your role').classes('text-h6 q-mt-lg text-center')

            with ui.row().classes('q-gutter-xl justify-center'):
                ui.button(
                    'I am a patient',
                    on_click=lambda: ui.navigate.to('/patient/login'),
                ).classes('q-px-xl q-py-md text-subtitle1')

                ui.button(
                    'I am a doctor',
                    on_click=lambda: ui.navigate.to('/doctor/login'),
                ).classes('q-px-xl q-py-md text-subtitle1')

# Patient LOGIN + DASHBOARD 

@ui.page('/patient/login')
def patient_login_page():
    global current_patient_id

    with ui.row().classes('w-full h-screen items-center justify-center'):
        with ui.column().classes('items-center q-gutter-md'):
            ui.label('Patient login').classes('text-h4 q-mb-md')

            with ui.card().classes('q-pa-lg q-ma-md'):
                pid_input = ui.input('Patient ID')
                last_name_input = ui.input('Last name')
                dob_input = ui.input('Date of birth (YYYY-MM-DD)')

                ui.label('') \
                    .classes('text-caption q-mt-sm')

                def do_login():
                    global current_patient_id
                    pid = (pid_input.value or '').strip()
                    last_name = (last_name_input.value or '').strip()
                    dob_str = (dob_input.value or '').strip()

                    patient = db.get_patient_by_id(pid)
                    if not patient:
                        ui.notify('Unknown patient ID', color='red')
                        return
                            
                    if patient.last_name.lower() != last_name.lower():
                        ui.notify('Surname does not match', color='red')
                        return

                    if patient.date_of_birth != dob_str:
                        ui.notify('Date of birth does not match', color='red')
                        return

                    current_patient_id = patient.patient_id
                    ui.notify('Login successful', color='green')
                    ui.navigate.to('/patient/dashboard')

                ui.button('Login as patient', on_click=do_login).classes('q-mt-md')

            ui.button(
                'Back to start',
                on_click=lambda: ui.navigate.to('/'),
            ).classes('q-mt-md')

# Patient DASHBOARD + BOOKING PAGE

@ui.page('/patient/dashboard')
def patient_dashboard_page():
    if current_patient_id is None:
        ui.notify('Please login first', color='red')
        ui.navigate.to('/patient/login')
        return

    patient = db.get_patient_by_id(current_patient_id)
    if not patient:
        ui.notify('Patient not found in database', color='red')
        ui.navigate.to('/patient/login')
        return
    
    all_active = db.get_all_active_bookings()
    my_bookings = [b for b in all_active if b.patient_id == current_patient_id]
    my_bookings.sort(key=lambda b: (b.appointment_date, b.time_slot))

    with ui.column().classes('items-center q-gutter-md q-mt-xl'):
        ui.label(f'Welcome, {patient.first_name} {patient.last_name}').classes('text-2xl')

        if patient.needs_checkup == 0:
            if my_bookings:
                ui.label('You are currently up to date with your visits.').classes('text-red-500')
            else:
                ui.label('Our records show that you need a follow up appointment.').classes('text-red-500')
        else:
            ui.label('You are currently up to date with your visits.').classes('text-green-600')
        
        ui.separator()
        ui.label('Your active appointments').classes('text-h6')

        if not my_bookings:
            ui.label('You have no active appointments.')
        else:
            for b in my_bookings:
                with ui.row().classes('items-center q-gutter-md'):
                    ui.label(f'{b.appointment_date} at {b.time_slot}')
                    ui.label(f'Doctor: {get_doctor_display_name(b.doctor_id)}')
                    ui.button(
                        'Cancel',
                        on_click=lambda bid=b.booking_id: (
                            bm.cancel_appointment(bid),
                            ui.notify('Appointment cancelled', color='green'),
                            ui.navigate.to('/patient/dashboard'),
                        ),
                    )

        ui.separator()
        with ui.row().classes('q-gutter-md'):
            ui.button(
                'Book or manage appointment',
                on_click=lambda: ui.navigate.to('/patient/book'),
            )
            ui.button(
                'Log out',
                on_click=lambda: (
                    setattr(__import__(__name__), 'current_patient_id', None),
                    ui.navigate.to('/')
                ),
            )

# Patient BOOKING PAGE

@ui.page('/patient/book')
def patient_booking_page():
    if current_patient_id is None:
        ui.notify('Please login first', color='red')
        ui.navigate.to('/patient/login')
        return

    PATIENT_ID = current_patient_id

    ui.add_head_html("""
    <style>
      .force-center {
        width: 100% !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
      }
      .cancel-enabled {
        opacity: 1 !important;
        cursor: pointer !important;
      }
      .cancel-disabled {
        opacity: 0.4 !important;
        cursor: not-allowed !important;
      }
    </style>
    """)

    today = date.today()
    current_year = today.year
    current_month = today.month
    selected_date = None

    CAL_CARD = "w-[320px] shadow-xl border rounded-xl overflow-hidden bg-white p-0"
    CAL_HEADER = "bg-[#6f97d3] text-white p-4"
    CAL_GRID = "grid grid-cols-7 gap-1 p-3 text-center text-sm"
    DAY_LABEL = "text-gray-500 font-semibold py-1"

    CELL_BASE = "w-9 h-9 flex items-center justify-center rounded-full cursor-pointer select-none"
    CELL_AVAILABLE = "bg-[#6f97d3] text-white hover:brightness-95"
    CELL_SELECTED = "bg-[#3f6fb7] text-white"
    CELL_DISABLED = "text-gray-300 bg-transparent cursor-not-allowed opacity-40"
    CELL_NORMAL = "text-gray-800 hover:bg-gray-100"

    NAV_BTN = "text-lg font-bold px-2 hover:bg-white/20 rounded"
    MONTH_TITLE = "text-sm font-semibold text-gray-700"

    CANCEL_BASE = "bg-[#6f97d3] text-white text-xs font-bold px-4 py-2 rounded transition-opacity"

    # Helper functions

# this rule is that doctors only work monday to friday
    def is_weekend(d: date) -> bool:
        return d.weekday() >= 5
# past dates cannot be booked so it only allows today and future dates
    def is_past(d: date) -> bool:
        return d < today
# formatting date to yyyy-mm-dd
    def fmt(d: date):
        return d.strftime("%Y-%m-%d")

# determining available dates for booking in the month this checks each day of the month to see if its available and then asks the booking manager if there are slots available on that date.
    def get_available_dates_for_month(year: int, month: int):
        avail = set()
        _, last_day = calendar.monthrange(year, month)
        for day in range(1, last_day + 1):
            d = date(year, month, day)
            if is_past(d) or is_weekend(d):
                continue
            if bm.get_available_slots(fmt(d)):
                avail.add(d)
        return avail
    
# checking if patient has an active booking
    def patient_has_active_booking():
        rows = db.get_all_active_bookings()
        return any(b.patient_id == PATIENT_ID for b in rows)
    
# Retrieves the specific active booking for this patient if it exists.
    def get_patient_active_booking():
        rows = db.get_all_active_bookings()
        for b in rows:
            if b.patient_id == PATIENT_ID:
                return b
        return None

    cal_container = ui.column()                                         # Holds the calendar grid
    slot_container = ui.column().classes("gap-2 items-center")          # Holds time slot buttons
    status_label = ui.label("").classes("text-gray-600")                # Shows messages like "Select a time"
    cancel_button = None                                                # Set later when creating the cancel button

    # Renders available time slots for the selected date.

    def render_timeslots(d: date):
        slot_container.clear()

        # BookingManager gives us available time slots
        available = bm.get_available_slots(fmt(d))
        time_options = ["09:00", "11:00", "13:00", "15:00"]

        active_booking = get_patient_active_booking()

        with slot_container:
            ui.label("Available time slots:").classes(
                "text-sm font-semibold text-gray-700 mb-1"
            )

            for s in time_options:

                 # If patient already has a booking, only that slot can appear active
                if active_booking:
                    free = (s == active_booking.time_slot)
                else:
                    free = (s in available)

                # Create a button for each time slot
                btn = ui.button(
                    s,
                    on_click=lambda slot=s: book_slot(d, slot)
                ).classes(
                    f"w-24 h-10 text-sm font-semibold rounded "
                    f"{'bg-[#6f97d3] text-white' if free else 'bg-gray-200 text-gray-500'}"
                )

                if not free or active_booking:
                    btn.disable()

    # HANDLE BOOKING LOGIC

    def book_slot(d: date, slot: str):
        # Prevent double booking by the same patient
        if patient_has_active_booking():
            ui.notify(
                "You already have an appointment. Cancel it before booking again.",
                color="red",
                position="bottom-left"
            )
            return
        
        # BookingManager handles all validation and saving
        result = bm.book_appointment(PATIENT_ID, fmt(d), slot)

        ui.notify(
            result,
            color="green" if "confirmed" in result.lower() else "red",
            position="bottom-left"
        )

        # Refresh the calendar and time slots after booking
        render_calendar()
        render_timeslots(d)
        update_cancel_button()

    # CANCEL APPOINTMENT

    def cancel_booking():
        nonlocal selected_date

        active_booking = get_patient_active_booking()
        if not active_booking:
            ui.notify(
                "You have no appointment to cancel.",
                color="red",
                position="bottom-left"
            )
            return

        result = bm.cancel_appointment(active_booking.booking_id)

        ui.notify(result, color="green", position="bottom-left")

        selected_date = None
        render_calendar()
        slot_container.clear()
        status_label.set_text("")
        update_cancel_button()

    # WHEN A DATE IS SELECTED

    def on_select_day(d: date):
        nonlocal selected_date
        selected_date = d
        render_calendar()
        render_timeslots(d)
        status_label.set_text(
            f"Doctor on duty for {fmt(d)}. Select a time."
        )

    # CHANGE VISIBLE MONTH

    def change_month(delta: int):
        nonlocal current_year, current_month, selected_date

        # Move forward or backward by 1 month
        new_month = current_month + delta
        new_year = current_year

        # Handle wrapping around December or January
        if new_month == 0:
            new_month = 12
            new_year -= 1
        elif new_month == 13:
            new_month = 1
            new_year += 1

        current_year = new_year
        current_month = new_month
        selected_date = None

        # Clear displays and rebuild calendar
        status_label.set_text("")
        slot_container.clear()
        render_calendar()

    # The main function to render the calendar UI ai was used to create the initial calendar structure and then it was manually adjusted to fit the design and functionality needed with the booking manager and database manager.

    def render_calendar():
        nonlocal selected_date

        cal_container.clear()

        # Ask BookingManager which dates have free slots
        avail_dates = get_available_dates_for_month(current_year, current_month)

        active_booking = get_patient_active_booking()
        booking_day = None

        # If patient already has a booking, highlight that day
        if active_booking:
            booking_day = date.fromisoformat(active_booking.appointment_date)
            selected_date = booking_day

        cal_obj = calendar.Calendar(firstweekday=6)
        weeks = cal_obj.monthdatescalendar(current_year, current_month)
        month_name = calendar.month_name[current_month]

        with cal_container:
            with ui.row().classes("force-center"):
                with ui.card().classes(CAL_CARD):

                    with ui.column().classes(CAL_HEADER + " items-center"):
                        ui.label(str(current_year)).classes("text-xs opacity-90")
                        ui.label(
                            selected_date.strftime("%a, %b %d")
                            if selected_date else f"{month_name[:3]} {current_year}"
                        ).classes("text-lg font-semibold")

                    with ui.row().classes("justify-between items-center px-3 py-2 bg-white w-full"):
                        ui.button("‹", on_click=lambda: change_month(-1)) \
                            .props("flat").classes(NAV_BTN)
                        ui.label(month_name).classes(MONTH_TITLE)
                        ui.button("›", on_click=lambda: change_month(1)) \
                            .props("flat").classes(NAV_BTN)

                    with ui.row().classes("justify-between px-3 w-full"):
                        for lab in ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]:
                            ui.label(lab).classes(DAY_LABEL).style("width:36px; text-align:center;")

                    with ui.element("div").classes(CAL_GRID):
                        for week in weeks:
                            for d in week:
                                in_month = (d.month == current_month)

                                if active_booking:
                                    disabled = (d != booking_day)
                                    is_available = (d == booking_day)
                                else:
                                    disabled = (not in_month) or is_past(d) or is_weekend(d)
                                    is_available = (d in avail_dates)

                                is_selected = (selected_date == d)

                                cls = CELL_BASE
                                if disabled:
                                    cls += " " + CELL_DISABLED
                                elif is_selected:
                                    cls += " " + CELL_SELECTED
                                elif is_available:
                                    cls += " " + CELL_AVAILABLE
                                else:
                                    cls += " " + CELL_NORMAL

                                cell = ui.label(str(d.day)).classes(cls)

                                if not disabled:
                                    cell.on("click", lambda e, dd=d: on_select_day(dd))

    # Update the cancel button state based on active booking

    def update_cancel_button():
        nonlocal cancel_button
        if cancel_button is None:
            return

        cancel_button._classes.clear()

        if patient_has_active_booking():
            cancel_button.enable()
            cancel_button.classes(CANCEL_BASE)
            cancel_button.classes("cancel-enabled")
        else:
            cancel_button.disable()
            cancel_button.classes(CANCEL_BASE)
            cancel_button.classes("cancel-disabled")

    ui.page_title("Patient appointment booking")

    with ui.row().style("""
        width:100%;
        display:flex;
        flex-direction:column;
        align-items:center;
        justify-content:flex-start;
        margin-top:40px;
    """):

        ui.label("Patient appointment booking").classes("text-3xl font-bold")

        ui.label(
            "Our records show that you need a follow up appointment based on your last visit."
        ).classes("text-sm text-gray-600")

        ui.label("Select a date for your appointment").classes("text-lg font-semibold mt-3")

        with ui.column().style("""
            display:flex;
            flex-direction:column;
            align-items:center;
            width:100%;
        """):

            render_calendar()

            active_booking = get_patient_active_booking()
            if active_booking:
                booked_day = date.fromisoformat(active_booking.appointment_date)
                render_timeslots(booked_day)
                status_label.set_text(
                    f"You have an appointment on {fmt(booked_day)} at {active_booking.time_slot}."
                )

            slot_container
            status_label

        cancel_button = ui.button("CANCEL APPOINTMENT", on_click=cancel_booking)
        update_cancel_button()

    ui.button(
        "Back to dashboard",
        on_click=lambda: ui.navigate.to('/patient/dashboard'),
    ).classes("mt-4")

# Doctor LOGIN + DASHBOARD

@ui.page('/doctor/login')
def doctor_login_page():
    # Global variable acts as a simple session flag for logged in doctor
    global current_doctor_id

    with ui.row().classes('w-full h-screen items-center justify-center'):
        with ui.column().classes('items-center q-gutter-md'):
            ui.label('Doctor login').classes('text-h4 q-mb-md')

            with ui.card().classes('q-pa-lg q-ma-md'):
                did_input = ui.input('Doctor ID')
                last_name_input = ui.input('Last name')
                dob_input = ui.input('Date of birth (YYYY-MM-DD)')

                ui.label('') \
                    .classes('text-caption q-mt-sm')
                
                # Inner function handles the actual login logic
                def do_login():
                    global current_doctor_id
                    did = (did_input.value or '').strip()
                    last_name = (last_name_input.value or '').strip()
                    dob_str = (dob_input.value or '').strip()

                    # Read and clean user input
                    doctor = db.get_doctor_by_id(did)
                    if not doctor:
                        ui.notify('Unknown doctor ID', color='red')
                        return

                    # Basic validation using surname
                    if doctor.last_name.lower() != last_name.lower():
                        ui.notify('Surname does not match', color='red')
                        return

                    # Basic validation using surname and date of birth
                    if doctor.date_of_birth != dob_str:
                        ui.notify('Date of birth does not match', color='red')
                        return

                    current_doctor_id = doctor.doctor_id
                    ui.notify('Login successful', color='green')
                    ui.navigate.to('/doctor/dashboard')

                ui.button('Login as doctor', on_click=do_login).classes('q-mt-md')

            #button to return to landing page
            ui.button(
                'Back to start',
                on_click=lambda: ui.navigate.to('/'),
            ).classes('q-mt-md')

# Doctor DASHBOARD

@ui.page('/doctor/dashboard')
def doctor_dashboard_page():
    if current_doctor_id is None:
        ui.notify('Please login first', color='red')
        ui.navigate.to('/doctor/login')
        return

    doctor_id = current_doctor_id

    # Load doctor object to ensure id is valid
    doctor = db.get_doctor_by_id(doctor_id)
    if not doctor:
        ui.notify('Doctor not found in database', color='red')
        ui.navigate.to('/doctor/login')
        return

    doctor_name = doctor.last_name
    from_date = today_str()

      # All future bookings for this doctor fetched via DatabaseManager
    doctor_bookings = db.get_future_active_bookings_for_doctor(doctor_id, from_date)

    # Convert booking objects into table rows for NiceGUI table
    def build_rows(bookings):
        rows = []
        for b in bookings:
            p = db.get_patient_by_id(b.patient_id)
            if p:
                pname = f"{p.first_name} {p.last_name}"
            else:
                pname = "Unknown"
            rows.append({
                'appt_date': b.appointment_date,
                'time_slot': b.time_slot,
                'patient_id': b.patient_id,
                'patient_name': pname,
            })
        return rows
    
    # labels for the select box to choose appointment to reschedule or cancel
    def build_labels(bookings):
        labels_local = []
        for b in bookings:
            p = db.get_patient_by_id(b.patient_id)
            if p:
                pname = f"{p.first_name} {p.last_name}"
            else:
                pname = "Unknown"
            label = f"{b.appointment_date} {b.time_slot} - {pname} (ID {b.patient_id})"
            labels_local.append(label)
        return labels_local

    # Reuse same time slots as patient booking
    labels = build_labels(doctor_bookings)

    TIME_SLOTS = VALID_TIMES

    # Main layout of the doctor dashboard
    with ui.row().classes("w-full h-screen justify-center items-center"):
        with ui.column().classes("items-center q-gutter-lg"):

            ui.label("Doctor schedule portal").classes("text-h4 text-center")

            ui.label(
                f"This view shows all upcoming appointments for Doctor ID {doctor_id} "
                f"({get_doctor_display_name(doctor_id)}). Data comes from the shared Booking table."
            ).classes("text-body1 q-mx-xl text-center")

            ui.label("Upcoming appointments").classes("text-h6")

            table = ui.table(
                columns=[
                    {"name": "appt_date", "label": "Date", "field": "appt_date"},
                    {"name": "time_slot", "label": "Time", "field": "time_slot"},
                    {"name": "patient_id", "label": "Patient ID", "field": "patient_id"},
                    {"name": "patient_name", "label": "Patient name", "field": "patient_name"},
                ],
                rows=build_rows(doctor_bookings),
            ).classes("q-mt-sm")

            ui.label(
                "Select an appointment below to reschedule or cancel it."
            ).classes("q-mt-lg text-subtitle1")

            # Drop down used to choose which specific appointment to change
            select_appointment = ui.select(
                options=labels,
                label="Appointment",
            ).classes("w-96")

            # Shows a short text description of the selected appointment
            info_label = ui.label("").classes("text-subtitle2 q-mt-sm")

            # Dialog used when the doctor clicks reschedule
            with ui.dialog() as dialog:
                with ui.card().classes("q-pa-md q-gutter-md items-center"):
                    ui.label("Reschedule appointment").classes("text-h6")

                    # New date and time controls for rescheduling
                    new_date_picker = ui.date(value=date.today())
                    new_time_select = ui.select(
                        options=TIME_SLOTS,
                        label="Time slot",
                        value=TIME_SLOTS[0],
                    )

                    # Confirm button inside the dialog
                    def confirm_reschedule():
                        nonlocal doctor_bookings, labels

                        label_value = select_appointment.value
                        if label_value is None:
                            ui.notify(
                                "No appointment selected.",
                                color="red",
                                position="top",
                            )
                            dialog.close()
                            return

                        # Find index of the selected label so we can map back to booking
                        try:
                            idx = labels.index(label_value)
                        except ValueError:
                            ui.notify("Selection is no longer valid.", color="red")
                            dialog.close()
                            return

                        booking = doctor_bookings[idx]

                        # Handle date value coming back from NiceGUI date picker
                        d_val = new_date_picker.value
                        if isinstance(d_val, date):
                            new_date_str = d_val.isoformat()
                            new_date_obj = d_val
                        else:
                            try:
                                new_date_obj = datetime.strptime(str(d_val), "%Y-%m-%d").date()
                                new_date_str = new_date_obj.isoformat()
                            except Exception:
                                ui.notify("Invalid date selected.", color="red")
                                return

                        new_time = new_time_select.value


                        # Validation rules for rescheduling
                        if new_date_obj < date.today():
                            ui.notify("Cannot move to a past date.", color="red")
                            return

                        if new_date_obj.weekday() >= 5:
                            ui.notify("Doctor only works Monday to Friday.", color="red")
                            return

                        if new_time not in TIME_SLOTS:
                            ui.notify("Invalid time slot.", color="red")
                            return
                        
                        # Check database for collisions at that date and time
                        same_day = db.get_active_bookings_for_date(doctor_id, new_date_str)
                        for b in same_day:
                            if b.time_slot == new_time and b.booking_id != booking.booking_id:
                                ui.notify("That time slot is already booked.", color="red")
                                return

                        # Use Mark's BookingManager method to apply the change
                        bm.reschedule_appointment(booking.booking_id, new_date_str, new_time)

                        ui.notify(
                            "Appointment rescheduled.",
                            color="green",
                            position="top",
                        )
                        dialog.close()

                        # Refresh table and select after modifying bookings
                        doctor_bookings = db.get_future_active_bookings_for_doctor(doctor_id, from_date)
                        table.rows = build_rows(doctor_bookings)
                        labels = build_labels(doctor_bookings)
                        select_appointment.options = labels
                        select_appointment.value = None
                        info_label.text = ""

                    ui.button("Confirm", on_click=confirm_reschedule)
                    ui.button("Cancel", on_click=dialog.close)

            # Cancel button handler from doctor side
            def cancel_selected():
                nonlocal doctor_bookings, labels

                label_value = select_appointment.value
                if label_value is None:
                    ui.notify(
                        "Please select an appointment to cancel.",
                        color="red",
                        position="top",
                    )
                    return

                try:
                    idx = labels.index(label_value)
                except ValueError:
                    ui.notify("Selection is no longer valid.", color="red")
                    return

                booking = doctor_bookings[idx]

                # Cancel uses BookingManager, not raw SQL, which keeps logic in one place
                bm.cancel_appointment(booking.booking_id)

                ui.notify(
                    f"Appointment on {booking.appointment_date} at {booking.time_slot} cancelled.",
                    color="green",
                    position="top",
                )

                # Reload latest data into table and select component
                doctor_bookings = db.get_future_active_bookings_for_doctor(doctor_id, from_date)
                table.rows = build_rows(doctor_bookings)
                labels = build_labels(doctor_bookings)
                select_appointment.options = labels
                select_appointment.value = None
                info_label.text = ""

            # Reschedule button handler, opens the dialog
            def reschedule_selected():
                label_value = select_appointment.value
                if label_value is None:
                    ui.notify(
                        "Please select an appointment to reschedule.",
                        color="red",
                        position="top",
                    )
                    return

                try:
                    idx = labels.index(label_value)
                except ValueError:
                    ui.notify("Selection is no longer valid.", color="red")
                    return

                booking = doctor_bookings[idx]

                # Show current booking information to the doctor
                info_label.text = (
                    f"Rescheduling appointment on {booking.appointment_date} at {booking.time_slot} "
                    f"for patient ID {booking.patient_id}."
                )

                # Pre fill dialog controls with existing date and time
                new_date_picker.value = date.fromisoformat(booking.appointment_date)
                new_time_select.value = booking.time_slot

                dialog.open()

            # Reload data from the database without restarting app
            def refresh_view():
                nonlocal doctor_bookings, labels
                doctor_bookings = db.get_future_active_bookings_for_doctor(doctor_id, from_date)
                table.rows = build_rows(doctor_bookings)
                labels = build_labels(doctor_bookings)
                select_appointment.options = labels
                select_appointment.value = None
                info_label.text = ""

            # Row of control buttons under the table
            with ui.row().classes("q-mt-md q-gutter-sm justify-center"):
                ui.button("Reschedule selected", on_click=reschedule_selected)
                ui.button("Cancel selected", on_click=cancel_selected, color="negative")
                ui.button("Refresh", on_click=refresh_view)
                ui.button(
                    "Log out",
                    on_click=lambda: (
                        setattr(__import__(__name__), 'current_doctor_id', None),
                        ui.navigate.to('/')
                    ),
                )

# Run the NiceGUI application for the whole project
ui.run(title="Clinic Portal", reload=False, port=8082)
