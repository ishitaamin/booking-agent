import os
import asyncio
import logging
from datetime import datetime, timezone
from fastapi import FastAPI, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import pandas as pd

from chatbot import llm_reply
from mailer import send_booking_email
from mem0_client import mem0_get, mem0_set
from excel_utils import save_booking_to_excel

# ---------------- Setup ----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("whatsapp_bot")

load_dotenv()
EXCEL_FILE = "moviedb.xlsx"

# Load Excel sheets
movies_df = pd.read_excel(EXCEL_FILE, sheet_name="Moviename", engine="openpyxl")
screens_df = pd.read_excel(EXCEL_FILE, sheet_name="screen", engine="openpyxl")
users_df = pd.read_excel(EXCEL_FILE, sheet_name="user", engine="openpyxl")
bookings_df = pd.read_excel(EXCEL_FILE, sheet_name="booking", engine="openpyxl")
showtimes_df = pd.read_excel(EXCEL_FILE, sheet_name="showtime", engine="openpyxl")

# In-memory session store
sessions = {}

# FastAPI app
app = FastAPI(title="Movie Booking Bot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Helpers ----------------

async def append_stm(phone: str, message: dict, limit: int = 10):
    """Append message to session STM (short-term memory)."""
    session = sessions.get(phone, {})
    stm = session.get("stm", [])
    stm.append(message)
    if len(stm) > limit:
        stm = stm[-limit:]
    session["stm"] = stm
    sessions[phone] = session

async def make_context(session: dict):
    """Build context for LLM based on session."""
    ctx = {}
    ctx["movies"] = movies_df[["title", "rating"]].to_dict(orient="records")

    movie_title = session.get("movieTitle")
    if movie_title:
        st = showtimes_df[showtimes_df["movieTitle"].str.lower() == movie_title.lower()]
        st_list = []
        for showtime_id, group in st.groupby("showtimeId"):
            available = group[group["available"] == True]["seat"].astype(str).tolist()
            st_list.append({
                "showtimeId": showtime_id,
                "startTime": group.iloc[0]["startTime"].strftime("%d-%m-%Y %H:%M"),
                "duration": group.iloc[0]["duration"],
                "screenName": group.iloc[0]["screenName"],
                "available_count": len(available),
                "price": group.iloc[0]["price"],
                "seats": available,
            })
        ctx["showtimes"] = st_list

    showtime_id = session.get("showtimeId")
    if showtime_id:
        show = showtimes_df[showtimes_df["showtimeId"] == showtime_id]
        if not show.empty:
            ctx["available_seats"] = show[show["available"] == True]["seat"].astype(str).tolist()

    ctx["stm"] = session.get("stm", [])
    ctx["ltm"] = mem0_get(session.get("phone")) or []
    return ctx

async def try_book_seats_excel(showtime_id, seats, user_email, user_name, phone):
    """Book seats and save to Excel."""
    global bookings_df, showtimes_df, users_df

    seats = [str(s) for s in seats]
    st = showtimes_df[showtimes_df["showtimeId"] == showtime_id]
    if st.empty:
        return {"success": False, "message": "Showtime not found"}

    available = st[st["available"] == True]["seat"].astype(str).tolist()
    if not all(seat in available for seat in seats):
        return {"success": False, "message": "Some seats are not available"}

    # Mark seats booked
    showtimes_df.loc[
        (showtimes_df["showtimeId"] == showtime_id) & (showtimes_df["seat"].isin(seats)),
        "available"
    ] = False

    # Create new booking
    new_booking = {
        "bookingId": len(bookings_df) + 1,
        "userId": user_email,
        "showtimeId": showtime_id,
        "seats": ",".join(seats),
        "totalPrice": len(seats) * st.iloc[0]["price"],
        "status": "confirmed",
        "CreatedAt": datetime.now()
    }
    bookings_df = pd.concat([bookings_df, pd.DataFrame([new_booking])], ignore_index=True)

    # Save new user if not exists
    if phone not in users_df["phone"].values:
        new_user = {"phone": phone, "name": user_name, "email": user_email}
        users_df = pd.concat([users_df, pd.DataFrame([new_user])], ignore_index=True)

    # Save all sheets
    try:
        with pd.ExcelWriter(EXCEL_FILE, engine="openpyxl") as writer:
            movies_df.to_excel(writer, sheet_name="Moviename", index=False)
            screens_df.to_excel(writer, sheet_name="screen", index=False)
            users_df.to_excel(writer, sheet_name="user", index=False)
            bookings_df.to_excel(writer, sheet_name="booking", index=False)
            showtimes_df.to_excel(writer, sheet_name="showtime", index=False)
    except Exception as e:
        logger.error("Failed to save Excel: %s", e)
        return {"success": False, "message": "Failed to save booking"}

    # Save booking to external Excel log
    save_booking_to_excel({
        "bookingId": new_booking["bookingId"],
        "name": user_name,
        "phone": phone,
        "email": user_email,
        "movie": st.iloc[0]["movieTitle"],
        "showtime": st.iloc[0]["startTime"].strftime("%d-%m-%Y %H:%M"),
        "seats": seats
    })

    # Send email asynchronously
    asyncio.create_task(
        send_booking_email(
            user_email, st.iloc[0]["movieTitle"],
            st.iloc[0]["startTime"].strftime("%d-%m-%Y %H:%M"),
            seats, name=user_name, phone=phone
        )
    )

    return {"success": True, "bookingId": new_booking["bookingId"], "seats": seats}

# ---------------- Webhook ----------------

@app.post("/whatsapp")
async def whatsapp_webhook(Body: str = Form(...), From: str = Form(...)):
    phone = From.replace("whatsapp:", "")
    text = Body.strip()
    logger.info("Incoming message from %s: %s", phone, text)

    # Get or create session
    session = sessions.get(phone)
    if not session:
        session = {
            "phone": phone,
            "stage": "greeting",
            "stm": [],
            "ltm": mem0_get(phone),
            "createdAt": datetime.now(timezone.utc)
        }
        user_row = users_df[users_df["phone"] == phone]
        if not user_row.empty:
            session["name"] = user_row.iloc[0]["name"]
            session["email"] = user_row.iloc[0]["email"]
        sessions[phone] = session

    await append_stm(phone, {"user": text})
    context = await make_context(session)

    # Call LLM
    llm_out = await llm_reply(text, session.get("stage"), context, session)
    logger.debug("LLM output: %s", llm_out)

    # Update session from LLM output
    to_set = llm_out.get("set", {}) or {}
    action = llm_out.get("action", {}) or {}
    reply_text = llm_out.get("reply", "Sorry, I couldn't understand that.")

    for k, v in to_set.items():
        if k in {"movieTitle", "showtimeId", "seats", "name", "email", "stage"}:
            session[k] = v

    # Advance stage if not explicitly set
    if "stage" not in to_set:
        # Automatic stage advancement handled inside LLM prompt
        session["stage"] = session.get("stage", "greeting")

    # Handle booking confirmation
    if action.get("confirm_booking"):
        showtime_id = session.get("showtimeId")
        seats = session.get("seats")
        email = session.get("email")
        name = session.get("name")
        if isinstance(seats, (str, int)):
            seats = [str(seats)]
        if showtime_id and seats and email and name:
            res = await try_book_seats_excel(showtime_id, seats, email, name, phone)
            if res.get("success"):
                session["bookingId"] = res["bookingId"]
                session["stage"] = "feedback"
                reply_text = f"✅ Booking confirmed for {name}! Seats: {', '.join(seats)}. Confirmation sent to {email}."
            else:
                reply_text = res.get("message", "Failed to book seats.")

    await append_stm(phone, {"bot": reply_text})
    sessions[phone] = session
    logger.info("Replying to %s: %s", phone, reply_text)

    twiml = MessagingResponse()
    twiml.message(reply_text)
    return PlainTextResponse(str(twiml), media_type="application/xml")
