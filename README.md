# Inventory Management System

A web-based inventory management system built with Flask and SQLAlchemy.

## Features

- Item management (add, edit, delete)
- Bill generation
- Customer management
- Inventory history tracking
- Quotation management
- Sales analytics
- PDF report generation

## Dependencies

- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- python-dotenv
- reportlab
- Werkzeug
- gunicorn
- psycopg2-binary

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/inventory-system.git
cd inventory-system
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
export FLASK_APP=app.py
export FLASK_ENV=development
```

5. Initialize the database:
```bash
flask db upgrade
```

6. Run the application:
```bash
flask run
```

## Usage

1. Access the application at `http://localhost:5000`
2. Add items to your inventory
3. Create bills for customers
4. Track inventory history
5. Generate quotations
6. View sales analytics

## Deployment

The application can be deployed on Render.com:

1. Create a new Web Service
2. Connect your GitHub repository
3. Set the following environment variables:
   - `FLASK_APP=app.py`
   - `FLASK_ENV=production`
   - `DATABASE_URL=your_postgresql_url`
   - `SECRET_KEY=your_secret_key`

## License

This project is licensed under the MIT License. 