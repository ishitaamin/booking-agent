# booking.py
import re
import logging
from typing import List, Union, Optional, Dict, Any
from pymongo import ReturnDocument

logger = logging.getLogger(__name__)

async def try_book_seats(db, showtime_id: str, seats: Union[int, List[str]],
                         user_id: Optional[str] = None, user_email: Optional[str] = None
                         ) -> Dict[str, Any]:
    """
    Attempt to book seats for a showtime atomically.

    - seats can be:
        - List[str] : explicit seat IDs to book (e.g. ["A1","A2"])
        - int       : number of seats to allocate; function will pick best seats.

    Returns:
        {"success": bool, "message": str, "bookingId": Optional[str], "seats": Optional[List[str]]}
    """
    if not showtime_id:
        return {"success": False, "message": "Missing showtime_id."}
    if not seats:
        return {"success": False, "message": "No seats requested."}

    try:
        # Start a client session and transaction so seat update + booking insert are atomic
        async with db.client.start_session() as session:
            async with session.start_transaction():
                # Read current showtime state inside the transaction
                show = await db.showtimes.find_one({"_id": showtime_id}, session=session)
                if not show:
                    return {"success": False, "message": "Showtime not found."}

                # Build list of currently available seat ids
                available = [s for s in show.get("seats", []) if s.get("available", False)]
                available_ids = [s["seat"] for s in available]

                # If seats requested as integer, pick best seats now (inside transaction)
                if isinstance(seats, int):
                    num = seats
                    seats_to_book = pick_best_seats(available_ids, num)
                    if not seats_to_book:
                        return {"success": False,
                                "message": f"Not enough seats available. Requested {num}, available {len(available_ids)}."}
                    seats = seats_to_book
                else:
                    # validate type
                    if not isinstance(seats, list):
                        return {"success": False, "message": "Invalid seats format; must be list or int."}
                    # check all requested seats exist & are available
                    seats = [str(s) for s in seats]
                    missing = [s for s in seats if s not in available_ids]
                    if missing:
                        return {"success": False,
                                "message": f"Some seats are not available: {', '.join(missing)}"}

                # Prepare a query that requires each seat to still be available
                seat_checks = [{"seats": {"$elemMatch": {"seat": s, "available": True}}} for s in seats]
                query = {"_id": showtime_id, "$and": seat_checks}

                # Prepare arrayFilters and set updates to mark those seats unavailable
                array_filters_named = []
                set_updates = {}
                for idx, s in enumerate(seats):
                    name = f"elem{idx}"
                    array_filters_named.append({f"{name}.seat": s})
                    set_updates[f"seats.$[{name}].available"] = False

                update_doc = {"$set": set_updates}

                # Use find_one_and_update - if None returned, the match failed (some seat became unavailable)
                updated = await db.showtimes.find_one_and_update(
                    query,
                    update_doc,
                    array_filters=array_filters_named,
                    session=session,
                    return_document=ReturnDocument.AFTER
                )

                if not updated:
                    return {"success": False,
                            "message": "One or more seats were no longer available. Please refresh and try different seats."}

                # Insert booking record (part of transaction)
                booking_doc = {
                    "userId": user_id,
                    "userEmail": user_email,
                    "showtimeId": showtime_id,
                    "seats": seats,
                }
                r = await db.bookings.insert_one(booking_doc, session=session)
                return {"success": True, "bookingId": str(r.inserted_id), "seats": seats}

    except Exception as e:
        logger.exception("DB error while attempting to book seats")
        return {"success": False, "message": f"DB error: {e}"}


def pick_best_seats(available_ids: List[str], n: int) -> Optional[List[str]]:
    """
    Try to find `n` contiguous seats in the same row (if seat ids use a pattern like A12).
    If contiguous not found, fallback to first-n available seats.

    Returns list of seat ids or None if not enough seats.
    """
    if len(available_ids) < n:
        return None

    pattern = re.compile(r"^([A-Za-z]+)?\s*(\d+)$")
    from collections import defaultdict
    rows = defaultdict(list)

    # Group seats by row prefix (letters) and keep column number + original id
    for sid in available_ids:
        m = pattern.match(sid.strip())
        if m:
            row = m.group(1) or ""
            col = int(m.group(2))
            rows[row].append((col, sid))
        else:
            # treat as row "" with col 0 so they appear in fallback
            rows[""].append((0, sid))

    # Look for contiguous run of length n in any row
    for row, lst in rows.items():
        lst.sort(key=lambda x: x[0])
        cols = [c for c, _ in lst]
        seats_sorted = [s for _, s in lst]
        for i in range(len(lst) - n + 1):
            window_cols = cols[i:i + n]
            contiguous = all(window_cols[j] + 1 == window_cols[j + 1] for j in range(len(window_cols) - 1))
            if contiguous:
                return seats_sorted[i:i + n]

    # fallback - return first n available
    return available_ids[:n]
