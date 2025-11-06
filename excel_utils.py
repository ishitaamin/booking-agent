# excel_utils.py
import pandas as pd
from datetime import datetime

EXCEL_FILE = "moviedb.xlsx"

def save_booking_to_excel(booking_data: dict):
    """
    Save booking entry into moviedb.xlsx -> 'booking' sheet
    and update 'user' sheet if the user is new.
    """
    try:
        # Load all sheets
        xls = pd.ExcelFile(EXCEL_FILE, engine="openpyxl")
        movies_df = pd.read_excel(xls, sheet_name="Moviename")
        screens_df = pd.read_excel(xls, sheet_name="screen")
        users_df = pd.read_excel(xls, sheet_name="user")
        bookings_df = pd.read_excel(xls, sheet_name="booking")
        showtimes_df = pd.read_excel(xls, sheet_name="showtime")

        # --- Save Booking ---
        new_booking = {
            "bookingId": booking_data.get("bookingId"),
            "userId": booking_data.get("email"),
            "showtimeId": None,  # not provided here, already linked in chatbot
            "seats": ",".join(booking_data.get("seats", [])),
            "totalPrice": None,  # price is handled in chatbot
            "status": "confirmed",
            "CreatedAt": datetime.now()
        }
        bookings_df = pd.concat([bookings_df, pd.DataFrame([new_booking])], ignore_index=True)

        # --- Save User (if new) ---
        phone = booking_data.get("phone")
        if phone not in users_df["phone"].astype(str).values:
            new_user = {
                "phone": phone,
                "name": booking_data.get("name"),
                "email": booking_data.get("email"),
                "createdAt": datetime.now()
            }
            users_df = pd.concat([users_df, pd.DataFrame([new_user])], ignore_index=True)

        # --- Write back everything ---
        with pd.ExcelWriter(EXCEL_FILE, mode="a", if_sheet_exists="replace") as writer:
            movies_df.to_excel(writer, sheet_name="Moviename", index=False)
            screens_df.to_excel(writer, sheet_name="screen", index=False)
            users_df.to_excel(writer, sheet_name="user", index=False)
            bookings_df.to_excel(writer, sheet_name="booking", index=False)
            showtimes_df.to_excel(writer, sheet_name="showtime", index=False)

        print("Booking and user saved successfully into moviedb.xlsx")

    except Exception as e:
        print("Error saving booking:", e)
