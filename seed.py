import os
from datetime import datetime, timezone, timedelta
from pprint import pprint
from dotenv import load_dotenv
from pymongo import MongoClient
import random

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise SystemExit("MONGO_URI not found in .env")

client = MongoClient(MONGO_URI)
db = client["moviedb"]

# ---------- Helpers ----------
def gen_seats(rows, cols):
    """
    Generate seats with categories:
    - First 2 rows = VIP
    - Middle rows = Premium
    - Last rows = Regular
    """
    seats = []
    for r in range(rows):
        row_char = chr(65 + r)  # A, B, C...
        if r < 2:
            seat_type = "vip"
        elif r < rows - 2:
            seat_type = "premium"
        else:
            seat_type = "regular"

        for c in range(1, cols + 1):
            seats.append({
                "seat": f"{row_char}{c}",
                "type": seat_type,
                "available": True
            })
    return seats

def calc_price(base_price, start_time, seat_type):
    """Dynamic pricing with seat category multiplier"""
    price = base_price

    # Morning discount (before 1pm)
    if start_time.hour < 13:
        price -= 50
    # Evening premium (after 6pm)
    elif start_time.hour >= 18:
        price += 30
    # Weekend surcharge
    if start_time.weekday() >= 5:
        price += 20

    # Seat type multiplier
    if seat_type == "premium":
        price += 50
    elif seat_type == "vip":
        price += 100

    return max(price, 100)

# ---------- Main ----------
def main():
    print("Clearing old data...")
    db.movies.delete_many({})
    db.screens.delete_many({})
    db.showtimes.delete_many({})
    db.users.delete_many({})
    db.bookings.delete_many({})

    # 5 Movies
    movies = [
        {"_id": "m1", "title": "Dil Chahta Hai", "durationMin": 150, "language": "Hindi", "genre": ["Drama","Friendship"], "rating": 8.0},
        {"_id": "m2", "title": "3 Idiots", "durationMin": 170, "language": "Hindi", "genre": ["Comedy","Drama"], "rating": 8.5},
        {"_id": "m3", "title": "Andhadhun", "durationMin": 140, "language": "Hindi", "genre": ["Thriller","Mystery"], "rating": 8.2},
        {"_id": "m4", "title": "Zindagi Na Milegi Dobara", "durationMin": 155, "language": "Hindi", "genre": ["Adventure","Drama"], "rating": 8.3},
        {"_id": "m5", "title": "Chhichhore", "durationMin": 145, "language": "Hindi", "genre": ["Comedy","Drama"], "rating": 7.9}
    ]
    db.movies.insert_many(movies)

    # 3 Screens
    screens = [
        {"_id": "s1", "name": "Screen 1", "rows": 10, "cols": 12, "basePrice": 250},
        {"_id": "s2", "name": "Screen 2", "rows": 8, "cols": 10, "basePrice": 200},
        {"_id": "s3", "name": "Screen 3", "rows": 6, "cols": 8, "basePrice": 180}
    ]
    db.screens.insert_many(screens)

    print("Generating 7-day showtimes...")
    base_date = datetime(2025, 9, 20, tzinfo=timezone.utc)
    showtimes = []
    st_id = 1

    movie_cycle = movies[:]  # for round-robin assignment
    movie_idx = 0

    for day_offset in range(7):  # 7 days
        date = base_date + timedelta(days=day_offset)

        for screen in screens:
            start_time = date.replace(hour=10, minute=0)

            while start_time.hour < 23:
                # Round-robin movie assignment
                movie = movie_cycle[movie_idx % len(movie_cycle)]
                movie_idx += 1

                # Generate seats for this show
                all_seats = gen_seats(screen["rows"], screen["cols"])
                priced_seats = []
                for seat in all_seats:
                    seat["price"] = calc_price(screen["basePrice"], start_time, seat["type"])
                    priced_seats.append(seat)

                showtimes.append({
                    "_id": f"st{st_id}",
                    "movieId": movie["_id"],
                    "screenId": screen["_id"],
                    "startTime": start_time,
                    "duration": movie["durationMin"],
                    "seats": priced_seats
                })
                st_id += 1

                start_time += timedelta(minutes=movie["durationMin"] + 20)

    db.showtimes.insert_many(showtimes)

    # Demo Users
    users = [
        {"_id": "u1", "name": "Ishita", "email": "ishitaamin3094@gmail.com", "phone": "+919327252376"},
        {"_id": "u2", "name": "Rohit", "email": "rohit@example.com", "phone": "+919888888888"},
        {"_id": "u3", "name": "Priya", "email": "priya@example.com", "phone": "+919777777777"}
    ]
    db.users.insert_many(users)

    # Sample Booking
    booking = {
        "_id": "b1",
        "userId": "u1",
        "showtimeId": "st1",
        "seats": ["A1", "A2"],  # reserved seat numbers
        "totalPrice": 600,
        "status": "confirmed",
        "createdAt": datetime.now(timezone.utc)
    }
    db.bookings.insert_one(booking)

    print("Seeding completed ✅")
    pprint({
        "movies": db.movies.count_documents({}),
        "screens": db.screens.count_documents({}),
        "showtimes": db.showtimes.count_documents({}),
        "users": db.users.count_documents({}),
        "bookings": db.bookings.count_documents({})
    })

if __name__ == "__main__":
    main()
