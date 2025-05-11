# ERP Website

A comprehensive Enterprise Resource Planning (ERP) system built with Flask, featuring inventory management, billing, customer management, and reporting capabilities.

## Features

- User Authentication with Role-based Access Control
- Inventory Management
- Customer Management
- Billing System with PDF Generation
- Quotation Management
- Sales Reports and Analytics
- Data Export (CSV)
- Settings Management

## Tech Stack

- Python 3.x
- Flask
- SQLAlchemy
- Flask-Login
- ReportLab (PDF Generation)
- Bootstrap (Frontend)

## Setup Instructions

1. Clone the repository:
```bash
git clone <repository-url>
cd erp-website
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Access the application at `http://localhost:5000`

## Default Admin Credentials

- Username: admin
- Password: admin123

## Environment Variables

Create a `.env` file in the root directory with the following variables:

```
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///erp.db
```

## License

MIT License 