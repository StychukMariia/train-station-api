# Train Station API

API service for train station management written on Django REST Framework (DRF).

## Features

- **JWT authenticated** (user registration and token generation)
- **Admin panel** at `/admin/`
- **API Documentation** via Swagger/OpenAPI
- **Managing stations, routes, and train types**
- **Managing trains** with dynamic capacity calculations (`cargo_num` & `places_in_cargo`)
- **Managing crew members** and assigning them to journeys
- **Managing journeys** (routes, departure/arrival times, crews)
- **Managing user orders and tickets** with automated seat validation
- **Database population** via custom management commands (`seed_db`)

---

## Configuration

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/danylott/train-station-api.git](https://github.com/danylott/train-station-api.git)
   cd train-station-api

2. **Configure environment variables:**
   Create a `.env` file in the root directory based on the `.env.example` template and fill in your actual database credentials and secret key:
   ```bash
   cp .env.example .env

## Installing and Running Locally (without Docker)

1. **Install PostgreSQL and create a database**

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt

4. **Run migrations and populate database (optional):**
   ```bash
   python manage.py migrate
   python manage.py seed_db

5. **Run the development server:**
   ```bash
   python manage.py runserver

## Run with Docker

Make sure **Docker** and **Docker Compose** are installed on your machine.

1. **Build and start containers:**
   ```bash
   docker-compose build
   docker-compose up

2. **Populate database with initial data inside Docker (optional):**
   ```bash
   docker-compose exec app python manage.py seed_db

## Getting Access

- **Create a user:** Register via `/api/user/register/`.
- **Get access token (JWT):** Obtain your token via `/api/user/token/`.
- **Admin panel:** Access the Django admin interface at `/admin/` (requires a superuser account).
- **API Documentation:** Explore interactive endpoints via Swagger at `/api/doc/swagger/` or ReDoc at `/api/doc/redoc/`.
- **Core Endpoints:** Manage stations, routes, train types, trains, crews, journeys, orders, and tickets through their respective API routes.
