from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field
import math                          # ✅ single import at the top (duplicate removed)

app = FastAPI()


# ==============================================================================
# MODELS
# ==============================================================================

class EnrollRequest(BaseModel):
    student_name: str = Field(..., min_length=2)
    course_id: int = Field(..., gt=0)
    email: str = Field(..., min_length=5)
    payment_method: str = "card"
    coupon_code: str = ""
    gift_enrollment: bool = False
    recipient_name: str = ""


class NewCourse(BaseModel):
    title: str = Field(..., min_length=2)
    instructor: str = Field(..., min_length=2)
    category: str = Field(..., min_length=2)
    level: str = Field(..., min_length=2)
    price: int = Field(..., ge=0)
    seats_left: int = Field(..., gt=0)


# ==============================================================================
# MOCK DATABASE
# ==============================================================================

courses = [
    {"id": 1, "title": "Full-Stack React",        "instructor": "Sarah Drasner",    "category": "Web Dev",      "level": "Intermediate", "price": 49,  "seats_left": 12},
    {"id": 2, "title": "Python for Data Science", "instructor": "Guido Van Rossum", "category": "Data Science", "level": "Beginner",     "price": 0,   "seats_left": 50},
    {"id": 3, "title": "Advanced Kubernetes",      "instructor": "Kelsey Hightower", "category": "DevOps",       "level": "Advanced",     "price": 99,  "seats_left": 5},
    {"id": 4, "title": "UI/UX Fundamentals",       "instructor": "Gary Simon",       "category": "Design",       "level": "Beginner",     "price": 25,  "seats_left": 20},
    {"id": 5, "title": "Django Rest Framework",    "instructor": "Tom Christie",     "category": "Web Dev",      "level": "Intermediate", "price": 40,  "seats_left": 8},
    {"id": 6, "title": "Machine Learning A-Z",     "instructor": "Kirill Eremenko",  "category": "Data Science", "level": "Advanced",     "price": 150, "seats_left": 15},
]

enrollments = []
enrollment_counter = 1

wishlist = []
wishlist_counter = 1


# ==============================================================================
# HELPERS
# ==============================================================================

def find_course(course_id: int):
    """Loop through the courses list and return the matching dict, or None."""
    for course in courses:
        if course["id"] == course_id:
            return course
    return None


def calculate_enrollment_fee(price: int, seats_left: int, coupon_code: str) -> float:
    """
    Apply discounts in order:
      1. Early-bird  — 10% off when more than 5 seats remain.
      2. STUDENT20   — additional 20% off.
         FLAT500     — flat 500 deducted (mutually exclusive with STUDENT20).
    Returns the final fee rounded to 2 decimal places.
    """
    final_price = float(price)
    if seats_left > 5:
        final_price *= 0.9
    if coupon_code == "STUDENT20":
        final_price *= 0.8
    elif coupon_code == "FLAT500":
        final_price = max(0.0, final_price - 500)
    return round(final_price, 2)


def filter_courses_logic(
    category: str = None,
    level: str = None,
    max_price: int = None,
    has_seats: bool = None,
):
    """
    Return a filtered copy of the courses list.
    Every condition is guarded by `is not None` so omitted params are ignored.
    """
    filtered = courses[:]
    if category is not None:
        filtered = [c for c in filtered if c["category"].lower() == category.lower()]
    if level is not None:
        filtered = [c for c in filtered if c["level"].lower() == level.lower()]
    if max_price is not None:
        filtered = [c for c in filtered if c["price"] <= max_price]
    if has_seats is True:
        filtered = [c for c in filtered if c["seats_left"] > 0]
    elif has_seats is False:
        filtered = [c for c in filtered if c["seats_left"] == 0]
    return filtered


# ==============================================================================
# ROUTES
#
# IMPORTANT — FastAPI matches routes top-to-bottom.
# All fixed paths  (/summary  /filter  /search  /sort  /page  /browse)
# must be declared BEFORE the variable path  /{course_id}
# or FastAPI will swallow the fixed paths as IDs.
# ==============================================================================


# ------------------------------------------------------------------------------
# ROOT
# ------------------------------------------------------------------------------

# HOME — Verify the API is running and return a welcome message.
@app.get("/")
def home():
    return {"message": "Welcome to LearnHub Online Courses"}


# ==============================================================================
# COURSES
# ==============================================================================

# GET ALL COURSES — Return every course in the catalogue with a total seat count.
@app.get("/courses")
def get_courses():
    total_seats = sum(c["seats_left"] for c in courses)
    return {
        "courses": courses,
        "total": len(courses),
        "total_seats_available": total_seats,
    }


# COURSES SUMMARY — High-level analytics: free count, priciest course, category breakdown.
# Fixed route — must stay above  GET /courses/{course_id}
@app.get("/courses/summary")
def get_courses_summary():
    if not courses:
        return {"message": "No courses available"}
    most_expensive = max(courses, key=lambda x: x["price"])
    category_counts: dict = {}
    for course in courses:
        cat = course["category"]
        category_counts[cat] = category_counts.get(cat, 0) + 1
    return {
        "total_courses": len(courses),
        "free_courses": len([c for c in courses if c["price"] == 0]),
        "most_expensive_course": {
            "title": most_expensive["title"],
            "price": most_expensive["price"],
        },
        "total_seats_available": sum(c["seats_left"] for c in courses),
        "category_breakdown": category_counts,
    }


# FILTER COURSES — Narrow the catalogue by category, level, max price, and/or seat availability.
# Fixed route — must stay above  GET /courses/{course_id}
@app.get("/courses/filter")
def get_filtered_courses(
    category: str = Query(None, description="e.g. Web Dev, Data Science, Design, DevOps"),
    level: str = Query(None, description="e.g. Beginner, Intermediate, Advanced"),
    max_price: int = Query(None, description="Upper price limit (inclusive)"),
    has_seats: bool = Query(None, description="True = seats available, False = fully booked"),
):
    results = filter_courses_logic(category, level, max_price, has_seats)
    return {"count": len(results), "results": results}


# SEARCH COURSES — Case-insensitive keyword search across title, instructor, and category.
# Fixed route — must stay above  GET /courses/{course_id}
@app.get("/courses/search")
def search_courses(
    keyword: str = Query(..., min_length=1, description="Term to look for in title, instructor, or category"),
):
    k = keyword.lower()
    results = [
        c for c in courses
        if k in c["title"].lower()
        or k in c["instructor"].lower()
        or k in c["category"].lower()
    ]
    if not results:
        return {"keyword": keyword, "total_found": 0, "message": "No courses matched your search.", "results": []}
    return {"keyword": keyword, "total_found": len(results), "results": results}


# SORT COURSES — Return the full catalogue ordered by price, title, or seats_left.
# Validates sort_by and order before sorting so bad inputs return a clear 400 error.
# Fixed route — must stay above  GET /courses/{course_id}
@app.get("/courses/sort")
def get_sorted_courses(
    sort_by: str = Query("price", description="Field to sort by: price, title, seats_left"),
    order: str = Query("asc", description="asc or desc"),
):
    allowed_sort_fields = ["price", "title", "seats_left"]
    if sort_by not in allowed_sort_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort field '{sort_by}'. Choose from: {', '.join(allowed_sort_fields)}",
        )
    if order.lower() not in ("asc", "desc"):
        raise HTTPException(
            status_code=400,
            detail="Invalid order value. Use 'asc' or 'desc'.",
        )
    is_reverse = order.lower() == "desc"
    sorted_list = sorted(
        courses,
        key=lambda x: x[sort_by].lower() if isinstance(x[sort_by], str) else x[sort_by],
        reverse=is_reverse,
    )
    return {
        "metadata": {
            "sorted_by": sort_by,
            "order": "descending" if is_reverse else "ascending",
            "total_count": len(sorted_list),
        },
        "courses": sorted_list,
    }


# PAGINATE COURSES — Slice the catalogue into pages of configurable size.
# Returns navigation helpers (has_next / has_previous) alongside the page slice.
# Fixed route — must stay above  GET /courses/{course_id}
@app.get("/courses/page")
def get_paginated_courses(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(3, ge=1, description="Items per page"),
):
    total_items = len(courses)
    total_pages = math.ceil(total_items / limit) if total_items > 0 else 1
    if page > total_pages and total_items > 0:
        raise HTTPException(
            status_code=404,
            detail=f"Page {page} does not exist. Total pages: {total_pages}",
        )
    start = (page - 1) * limit
    end = start + limit
    return {
        "metadata": {
            "current_page": page,
            "limit": limit,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        },
        "courses": courses[start:end],
    }


# BROWSE COURSES — Master endpoint: keyword search + multi-filter + sort + pagination in one call.
# Applies operations in order: filter -> sort -> paginate.
# Fixed route — must stay above  GET /courses/{course_id}
@app.get("/courses/browse")
def browse_courses(
    keyword: str = Query(None, description="Search term matched against title and instructor"),
    category: str = Query(None),
    level: str = Query(None),
    max_price: int = Query(None),
    sort_by: str = Query("price", description="price, title, seats_left"),
    order: str = Query("asc", description="asc or desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(3, ge=1),
):
    # Validate sort params up front so invalid values never reach sorted()
    allowed_sort_fields = ["price", "title", "seats_left"]
    if sort_by not in allowed_sort_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort field '{sort_by}'. Choose from: {', '.join(allowed_sort_fields)}",
        )
    if order.lower() not in ("asc", "desc"):
        raise HTTPException(
            status_code=400,
            detail="Invalid order value. Use 'asc' or 'desc'.",
        )

    # 1. FILTER
    results = courses[:]
    if keyword:
        k = keyword.lower()
        results = [
            c for c in results
            if k in c["title"].lower() or k in c["instructor"].lower()
        ]
    if category:
        results = [c for c in results if c["category"].lower() == category.lower()]
    if level:
        results = [c for c in results if c["level"].lower() == level.lower()]
    if max_price is not None:
        results = [c for c in results if c["price"] <= max_price]

    # 2. SORT
    is_reverse = order.lower() == "desc"
    results = sorted(
        results,
        key=lambda x: x[sort_by].lower() if isinstance(x[sort_by], str) else x[sort_by],
        reverse=is_reverse,
    )

    # 3. PAGINATE
    total_found = len(results)
    total_pages = math.ceil(total_found / limit) if total_found > 0 else 1
    start = (page - 1) * limit
    paginated = results[start: start + limit]

    return {
        "metadata": {
            "total_found": total_found,
            "total_pages": total_pages,
            "current_page": page,
            "page_limit": limit,
            "filters_applied": {
                "keyword": keyword,
                "category": category,
                "level": level,
                "max_price": max_price,
            },
            "sorting": {"field": sort_by, "order": order},
        },
        "results": paginated,
    }


# GET COURSE BY ID — Return full details for a single course using its numeric ID.
# Variable route — must stay BELOW all fixed  /courses/*  routes
@app.get("/courses/{course_id}")
def get_course(course_id: int):
    course = find_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return {"course": course}


# CREATE COURSE — Add a new course. Rejects duplicate titles (case-insensitive). Returns 201.
@app.post("/courses", status_code=status.HTTP_201_CREATED)
def create_course(course_data: NewCourse):
    title_exists = any(c["title"].lower() == course_data.title.lower() for c in courses)
    if title_exists:
        raise HTTPException(
            status_code=400,
            detail=f"A course titled '{course_data.title}' already exists.",
        )
    new_id = max(c["id"] for c in courses) + 1 if courses else 1
    new_course = {"id": new_id, **course_data.model_dump()}
    courses.append(new_course)
    return {"message": "Course created successfully", "course": new_course}


# UPDATE COURSE — Patch price and/or seats_left for an existing course.
# Only fields explicitly provided are changed; omitted fields stay unchanged.
@app.put("/courses/{course_id}")
def update_course(
    course_id: int,
    price: int = Query(None, ge=0, description="New price (0 = free)"),
    seats_left: int = Query(None, ge=0, description="New seat count"),
):
    course = find_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail=f"Course with ID {course_id} not found")
    updates_made = []
    if price is not None:
        course["price"] = price
        updates_made.append("price")
    if seats_left is not None:
        course["seats_left"] = seats_left
        updates_made.append("seats_left")
    if not updates_made:
        return {"message": "No updates provided", "course": course}
    return {"message": f"Updated: {', '.join(updates_made)}", "course": course}


# DELETE COURSE — Remove a course permanently.
# Blocked if any student is enrolled to protect data integrity.
@app.delete("/courses/{course_id}")
def delete_course(course_id: int):
    global courses
    course = find_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail=f"Course with ID {course_id} not found")
    # Enrollment records store the course title under the "course" key
    has_enrolled_students = any(e["course"] == course["title"] for e in enrollments)
    if has_enrolled_students:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete: students are currently enrolled in this course.",
        )
    courses = [c for c in courses if c["id"] != course_id]
    return {"message": f"Course '{course['title']}' deleted successfully"}


# ==============================================================================
# ENROLLMENTS
# Fixed routes (search / sort / page) must come BEFORE any variable /{id} route
# ==============================================================================

# GET ALL ENROLLMENTS — Return the complete enrollment history with a record count.
@app.get("/enrollments")
def get_enrollments():
    return {"total": len(enrollments), "enrollments": enrollments}


# SEARCH ENROLLMENTS — Find enrollment records by student name (case-insensitive partial match).
# Fixed route — must stay above any  /enrollments/{id}  route
@app.get("/enrollments/search")
def search_enrollments(
    student_name: str = Query(..., min_length=1, description="Student name to search for"),
):
    # Enrollment records store the student name under the key "student"
    results = [
        e for e in enrollments
        if student_name.lower() in e["student"].lower()
    ]
    if not results:
        return {
            "search_term": student_name,
            "total_found": 0,
            "message": "No enrollments found for this student.",
            "results": [],
        }
    return {"search_term": student_name, "total_found": len(results), "results": results}


# SORT ENROLLMENTS — Order the enrollment history by the final fee paid.
# Fixed route — must stay above any  /enrollments/{id}  route
@app.get("/enrollments/sort")
def sort_enrollments(
    order: str = Query("desc", description="asc or desc"),
):
    if order.lower() not in ("asc", "desc"):
        raise HTTPException(status_code=400, detail="Invalid order. Use 'asc' or 'desc'.")
    is_reverse = order.lower() == "desc"
    sorted_list = sorted(enrollments, key=lambda x: x["final_fee"], reverse=is_reverse)
    return {
        "sorted_by": "final_fee",
        "order": "descending" if is_reverse else "ascending",
        "total": len(sorted_list),
        "results": sorted_list,
    }


# PAGINATE ENROLLMENTS — Retrieve enrollment history in small, page-sized chunks.
# Fixed route — must stay above any  /enrollments/{id}  route
@app.get("/enrollments/page")
def paginate_enrollments(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(5, ge=1, description="Records per page"),
):
    total_items = len(enrollments)
    total_pages = math.ceil(total_items / limit) if total_items > 0 else 1
    start = (page - 1) * limit
    end = start + limit
    return {
        "metadata": {
            "current_page": page,
            "total_pages": total_pages,
            "total_records": total_items,
            "has_next": page < total_pages,
        },
        "enrollments": enrollments[start:end],
    }


# CREATE ENROLLMENT — Enroll a student in a course.
# Validates seat availability, handles gift enrollments, and applies pricing discounts.
@app.post("/enrollments")
def create_enrollment(request: EnrollRequest):
    global enrollment_counter

    # 1. Confirm the course exists
    course = find_course(request.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # 2. Confirm seats are available
    if course["seats_left"] == 0:
        raise HTTPException(status_code=400, detail="No seats available for this course")

    # 3. Gift enrollment requires a recipient name
    if request.gift_enrollment and request.recipient_name == "":
        raise HTTPException(status_code=400, detail="Recipient name is required for a gift enrollment")

    # 4. Calculate the fee with any applicable discounts
    final_fee = calculate_enrollment_fee(
        course["price"], course["seats_left"], request.coupon_code
    )
    discount = round(course["price"] - final_fee, 2)

    # 5. Build the enrollment record
    new_enrollment = {
        "id": enrollment_counter,
        "student": request.student_name,       # key "student" — used by search & delete checks
        "course": course["title"],             # key "course"  — used by delete_course check
        "course_id": course["id"],
        "original_price": course["price"],
        "discount": discount,
        "final_fee": final_fee,
        "gift": request.gift_enrollment,
        "recipient": request.recipient_name if request.gift_enrollment else None,
    }

    # 6. Persist and decrement the seat count
    enrollments.append(new_enrollment)
    course["seats_left"] -= 1
    enrollment_counter += 1

    return new_enrollment


# ==============================================================================
# WISHLIST
# Fixed routes (/wishlist/add  /wishlist/enroll-all) must come
# BEFORE the variable route  /wishlist/remove/{course_id}
# ==============================================================================

# GET WISHLIST — Return all saved wishlist items and the combined catalogue value.
@app.get("/wishlist")
def get_wishlist():
    total_value = sum(item["price_at_addition"] for item in wishlist)
    return {
        "total_items": len(wishlist),
        "total_wishlist_value": total_value,
        "items": wishlist,
    }


# ADD TO WISHLIST — Save a course to a student's wishlist.
# Rejects duplicate student + course combinations.
# Fixed route — must stay above  DELETE /wishlist/remove/{course_id}
@app.post("/wishlist/add")
def add_to_wishlist(
    student_name: str = Query(..., description="Name of the student"),
    course_id: int = Query(..., description="ID of the course to save"),
):
    global wishlist_counter

    course = find_course(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Block duplicate student + course combos
    duplicate = any(
        w["student_name"].lower() == student_name.lower() and w["course_id"] == course_id
        for w in wishlist
    )
    if duplicate:
        raise HTTPException(
            status_code=400,
            detail=f"'{course['title']}' is already in {student_name}'s wishlist",
        )

    wishlist_item = {
        "wishlist_id": wishlist_counter,
        "student_name": student_name,
        "course_id": course_id,
        "course_title": course["title"],
        "price_at_addition": course["price"],
    }
    wishlist.append(wishlist_item)
    wishlist_counter += 1

    return {"message": "Added to wishlist", "item": wishlist_item}


# ENROLL ALL FROM WISHLIST — Bulk-enroll a student in every course on their wishlist.
# Skips deleted courses and fully-booked courses. Clears enrolled items afterward. Returns 201.
# Fixed route — must stay above  DELETE /wishlist/remove/{course_id}
@app.post("/wishlist/enroll-all", status_code=status.HTTP_201_CREATED)
def enroll_all_from_wishlist(
    student_name: str = Query(..., description="Student whose wishlist to process"),
    payment_method: str = Query("card", description="Payment method for all enrollments"),
):
    global wishlist, enrollment_counter

    student_items = [
        w for w in wishlist if w["student_name"].lower() == student_name.lower()
    ]
    if not student_items:
        raise HTTPException(
            status_code=400,
            detail=f"No wishlist items found for '{student_name}'",
        )

    confirmed_enrollments = []
    grand_total = 0.0

    for item in student_items:
        course = find_course(item["course_id"])
        if not course:            # course was deleted after being wishlisted
            continue
        if course["seats_left"] == 0:
            continue

        final_fee = calculate_enrollment_fee(course["price"], course["seats_left"], "")
        discount = round(course["price"] - final_fee, 2)

        new_enrollment = {
            "id": enrollment_counter,
            "student": student_name,
            "course": course["title"],
            "course_id": course["id"],
            "original_price": course["price"],
            "discount": discount,
            "final_fee": final_fee,
            "gift": False,
            "recipient": None,
        }
        enrollments.append(new_enrollment)
        course["seats_left"] -= 1
        enrollment_counter += 1
        grand_total += final_fee
        confirmed_enrollments.append(new_enrollment)

    # Remove successfully enrolled courses from the student's wishlist
    enrolled_ids = {e["course_id"] for e in confirmed_enrollments}
    wishlist = [
        w for w in wishlist
        if not (
            w["student_name"].lower() == student_name.lower()
            and w["course_id"] in enrolled_ids
        )
    ]

    return {
        "message": f"Enrolled '{student_name}' in {len(confirmed_enrollments)} course(s)",
        "total_enrolled": len(confirmed_enrollments),
        "grand_total": round(grand_total, 2),
        "enrollments": confirmed_enrollments,
    }


# REMOVE FROM WISHLIST — Delete a specific course from a student's wishlist.
# Variable route — must stay BELOW all fixed  /wishlist/*  routes
@app.delete("/wishlist/remove/{course_id}")
def remove_from_wishlist(
    course_id: int,
    student_name: str = Query(..., description="Name of the student"),
):
    global wishlist

    item_exists = any(
        w["course_id"] == course_id
        and w["student_name"].lower() == student_name.lower()
        for w in wishlist
    )
    if not item_exists:
        raise HTTPException(status_code=404, detail="Item not found in this student's wishlist")

    wishlist = [
        w for w in wishlist
        if not (
            w["course_id"] == course_id
            and w["student_name"].lower() == student_name.lower()
        )
    ]
    return {"message": f"Course {course_id} removed from {student_name}'s wishlist"}
