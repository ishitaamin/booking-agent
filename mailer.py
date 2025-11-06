# mailer.py
import os
import asyncio
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import aiosmtplib

load_dotenv()
logger = logging.getLogger(__name__)

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))

async def send_booking_email(
    to_email: str,
    movie_title: str,
    showtime: str,
    seats: list,
    name: str = None,
    phone: str = None,
    price_per_seat: float = 15.0,  # Default, can be updated dynamically
    booking_ref: str = None
):
    """
    Send detailed booking confirmation email
    """
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = to_email
        msg["Subject"] = f"🎬 Booking Confirmation - {movie_title}"

        total_price = len(seats) * price_per_seat
        seats_details = "\n".join([f"{seat} - ₹{price_per_seat}" for seat in seats])

        body = f"""
Hello {name or 'User'},

Your booking for the movie "{movie_title}" is confirmed! ✅

🎟 Booking Details:
Booking Reference: {booking_ref or 'N/A'}
Movie: {movie_title}
Showtime: {showtime}
Seats Booked:
{seats_details}

Total Price: ₹{total_price}

📞 Contact: {phone or 'N/A'}

Thank you for booking with MovieBot!
Enjoy your movie 🍿

- MovieBot Team
"""
        msg.attach(MIMEText(body, "plain"))

        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=EMAIL_USER,
            password=EMAIL_PASS,
            start_tls=True
        )
        logger.info("Booking email sent to %s", to_email)
    except Exception as e:
        logger.error("Failed to send booking email: %s", str(e))
