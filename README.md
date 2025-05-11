# Inventory Management System

A simple web-based inventory management system with billing capabilities.

## Features

- Add and manage inventory items
- Track stock levels
- Create bills with multiple items
- Generate PDF bills
- SQLite database for data persistence

## Setup

1. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open your browser and navigate to `http://localhost:5000`

## Usage

1. **Adding Items**
   - Click on "Add Item" in the navigation bar
   - Fill in the item details (name, description, price, stock)
   - Submit the form

2. **Creating Bills**
   - Click on "Create Bill" in the navigation bar
   - Enter customer name
   - Select items and quantities
   - The total will be calculated automatically
   - Submit to generate the bill

3. **Viewing Inventory**
   - The home page shows all items in the inventory
   - Stock levels are updated automatically when bills are created

## Database

The application uses SQLite as its database. The database file (`inventory.db`) will be created automatically when you first run the application.

## PDF Bills

Bills are automatically generated as PDF files when created. They include:
- Bill number
- Customer name
- Date and time
- Itemized list of purchased items
- Total amount 