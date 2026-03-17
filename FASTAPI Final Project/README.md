# LearnHub — Online Course Platform API

A REST API built with **FastAPI** for managing an online course catalogue.  
Students can browse courses, enroll, save items to a wishlist, and bulk-enroll from it.

---

## Tech Stack

| Layer | Library |
|-------|---------|
| Framework | FastAPI 0.115 |
| Validation | Pydantic v2 |
| Server | Uvicorn |
| Language | Python 3.10+ |

---

## Project Structure

```
learnhub/
├── main.py           # All routes, models, helpers, and mock database
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

---

## Setup & Installation

**1. Clone or download the project**

```bash
git clone <your-repo-url>
cd learnhub
```

**2. Create and activate a virtual environment**

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Run the server**

```bash
uvicorn main:app --reload
```

**5. Open Swagger UI**

```
http://127.0.0.1:8000/docs
```

> All endpoints can be tested directly in Swagger without any external tool.

---

## Data Models

### `NewCourse` — used in `POST /courses`

| Field | Type | Rule |
|-------|------|------|
| `title` | str | min 2 characters |
| `instructor` | str | min 2 characters |
| `category` | str | min 2 characters |
| `level` | str | min 2 characters |
| `price` | int | ≥ 0 (0 = free) |
| `seats_left` | int | > 0 |

### `EnrollRequest` — used in `POST /enrollments`

| Field | Type | Rule | Default |
|-------|------|------|---------|
| `student_name` | str | min 2 characters | — |
| `course_id` | int | > 0 | — |
| `email` | str | min 5 characters | — |
| `payment_method` | str | — | `"card"` |
| `coupon_code` | str | — | `""` |
| `gift_enrollment` | bool | — | `false` |
| `recipient_name` | str | required when gift=true | `""` |

---

## API Endpoints

> ⚠️ **Route Order Rule** — FastAPI matches routes top-to-bottom.  
> Fixed paths (`/summary`, `/search`, `/filter`, `/sort`, `/page`, `/browse`)  
> are always declared **before** the variable path `/{id}` in the file.

---

### Root

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check — returns welcome message |

---

### Courses

| Method | Path | Description |
|--------|------|-------------|
| GET | `/courses` | List all courses + total seat count |
| GET | `/courses/summary` | Analytics: free count, priciest course, category breakdown |
| GET | `/courses/filter` | Filter by category, level, max\_price, has\_seats |
| GET | `/courses/search` | Keyword search across title, instructor, category |
| GET | `/courses/sort` | Sort by `price`, `title`, or `seats_left` |
| GET | `/courses/page` | Paginate catalogue (page + limit) |
| GET | `/courses/browse` | **Master endpoint** — search + filter + sort + paginate |
| GET | `/courses/{course_id}` | Get a single course by ID |
| POST | `/courses` | Add a new course (201) — rejects duplicate titles |
| PUT | `/courses/{course_id}` | Update price and/or seats\_left |
| DELETE | `/courses/{course_id}` | Delete a course — blocked if students are enrolled |

#### Query Parameters — `/courses/filter`

| Param | Type | Example |
|-------|------|---------|
| `category` | str | `Web Dev` |
| `level` | str | `Beginner` |
| `max_price` | int | `50` |
| `has_seats` | bool | `true` |

#### Query Parameters — `/courses/search`

| Param | Type | Required |
|-------|------|----------|
| `keyword` | str | ✅ |

#### Query Parameters — `/courses/sort`

| Param | Options | Default |
|-------|---------|---------|
| `sort_by` | `price`, `title`, `seats_left` | `price` |
| `order` | `asc`, `desc` | `asc` |

#### Query Parameters — `/courses/page`

| Param | Type | Default |
|-------|------|---------|
| `page` | int ≥ 1 | `1` |
| `limit` | int ≥ 1 | `3` |

#### Query Parameters — `/courses/browse`

| Param | Type | Default | Notes |
|-------|------|---------|-------|
| `keyword` | str | — | Searches title + instructor |
| `category` | str | — | Exact match (case-insensitive) |
| `level` | str | — | Exact match (case-insensitive) |
| `max_price` | int | — | Inclusive upper bound |
| `sort_by` | str | `price` | `price`, `title`, `seats_left` |
| `order` | str | `asc` | `asc` or `desc` |
| `page` | int ≥ 1 | `1` | |
| `limit` | int ≥ 1 | `3` | |

---

### Enrollments

| Method | Path | Description |
|--------|------|-------------|
| GET | `/enrollments` | List all enrollment records |
| GET | `/enrollments/search` | Search by student name (partial, case-insensitive) |
| GET | `/enrollments/sort` | Sort by `final_fee` |
| GET | `/enrollments/page` | Paginate enrollment history |
| POST | `/enrollments` | Create a new enrollment |

#### Pricing Logic — `POST /enrollments`

Discounts are applied in order:

1. **Early-bird** — 10% off when `seats_left > 5`
2. **Coupon `STUDENT20`** — additional 20% off
3. **Coupon `FLAT500`** — flat ₹500 deducted *(mutually exclusive with STUDENT20)*

#### Gift Enrollment

Set `gift_enrollment: true` and provide a non-empty `recipient_name`.  
Omitting the recipient name returns a `400` error.

---

### Wishlist

| Method | Path | Description |
|--------|------|-------------|
| GET | `/wishlist` | View all saved items + total value |
| POST | `/wishlist/add` | Add a course to a student's wishlist |
| POST | `/wishlist/enroll-all` | Enroll in every wishlisted course + clear them (201) |
| DELETE | `/wishlist/remove/{course_id}` | Remove one course from a student's wishlist |

#### Query Parameters — `/wishlist/add`

| Param | Type | Required |
|-------|------|----------|
| `student_name` | str | ✅ |
| `course_id` | int | ✅ |

> Duplicate `student_name + course_id` combinations are rejected with `400`.

#### Query Parameters — `/wishlist/enroll-all`

| Param | Type | Default |
|-------|------|---------|
| `student_name` | str | ✅ required |
| `payment_method` | str | `card` |

> Skips any course that has been deleted or has no seats left since being wishlisted.

---

## Discount & Pricing Reference

| Condition | Discount |
|-----------|----------|
| `seats_left > 5` | 10% early-bird |
| Coupon `STUDENT20` | 20% off (applied after early-bird) |
| Coupon `FLAT500` | ₹500 flat off (applied after early-bird) |
| Senior citizen flag | 15% additional off |

---

## Error Reference

| Code | Meaning | Example |
|------|---------|---------|
| `200` | OK | Successful GET / PUT / DELETE |
| `201` | Created | POST /courses, POST /enrollments (wishlist flow) |
| `400` | Bad Request | Duplicate title, no seats, missing recipient |
| `404` | Not Found | Invalid ID, page out of range |
| `422` | Unprocessable Entity | Pydantic validation failure (e.g. quantity=0) |

---

## Sample Workflow

```
# 1. Browse available courses
GET /courses

# 2. Search for a Python course
GET /courses/search?keyword=python

# 3. Enroll with a coupon
POST /enrollments
{
  "student_name": "Aisha Kumar",
  "course_id": 2,
  "email": "aisha@example.com",
  "coupon_code": "STUDENT20"
}

# 4. Save a course to wishlist
POST /wishlist/add?student_name=Aisha+Kumar&course_id=5

# 5. Bulk-enroll from wishlist
POST /wishlist/enroll-all?student_name=Aisha+Kumar
```

---

## Notes

- All data is stored **in-memory**. Restarting the server resets all enrollments and wishlist items; the base course catalogue reloads from the hardcoded list in `main.py`.
- Swagger UI at `/docs` and ReDoc at `/redoc` are available automatically.
