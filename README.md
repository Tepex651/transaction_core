# Wallet & Transaction Service

This project implements a simple Wallet and Transaction system with a transfer endpoint, concurrency safety, and notifications.

## Features

* **Wallet** and **Transaction** models.
* POST `/api/transfer`: transfer funds from Wallet A to Wallet B.
* **Race Condition Protection**: Handles multiple simultaneous requests to prevent double spending.
* **Commission**: Transfers above 1000 units are charged a 10% commission to the technical `admin` wallet.
* **Atomicity**: All operations (debit, credit, commission) are executed atomically.
* **Notifications**: Sends fake notifications to the recipient via Celery tasks with retries on failure.

---

## Environment Variables (example `.env`)

```env
DJANGO_SECRET_KEY=<your_secret_key>
POSTGRES_DB="wallet"
POSTGRES_USER="user"
POSTGRES_PASSWORD="password"
POSTGRES_HOST="127.0.0.1"
POSTGRES_PORT=5432

RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest
RABBITMQ_HOST=localhost
RABBITMQ_PORT=5672
RABBITMQ_MANAGER_PORT=15672
```

---

## Manual Start (Step-by-step)

1. **Install dependencies**

Follow the official UV installation instructions: [https://astral.sh/uv](https://astral.sh/uv)

Then, inside your project directory:

```bash
uv install
uv sync --locked
```

2. **Run database migrations**

```bash
uv run python manage.py migrate
```

3. **Start Django server**

```bash
uv run python manage.py runserver
```

4. **Start Celery worker**

```bash
uv run celery -A config worker -l info
```

5. **Optional: Run tests**

```bash
uv run python manage.py test
```

---

## Automatic Start with Docker Compose

This method runs all components inside Docker containers including Django, Celery, PostgreSQL, and RabbitMQ.

### 1. Build and start services

```bash
docker-compose up --build
```

This will:

* Build the Docker image.
* Start PostgreSQL and RabbitMQ containers.
* Run migrations automatically.
* Start the Django server on `0.0.0.0:8000`.
* Start the Celery worker.

### 2. Stop services

```bash
docker-compose down
```

To also remove volumes (e.g., database data):

```bash
docker-compose down -v
```

### 3. Access services

* Django: `http://localhost:8000/`
* RabbitMQ Management: `http://localhost:15672/` (use credentials from `.env`)

### 4. Run commands inside the container

```bash
docker-compose exec web uv run python manage.py <command>
```

Example, run migrations manually:

```bash
docker-compose exec web uv run python manage.py migrate
```
