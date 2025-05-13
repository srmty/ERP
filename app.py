from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, Response, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import os
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from werkzeug.security import generate_password_hash, check_password_hash
from io import BytesIO
from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.graphics.shapes import Drawing
from dotenv import load_dotenv
from flask_login import LoginManager, UserMixin, login_required, login_user, current_user

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Production-ready configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key')  # Use environment variable in production
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///erp.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# User Model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='cashier')  # admin, cashier, manager
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Database Models
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    hsn_sac_number = db.Column(db.String(20), nullable=True)  # HSN/SAC number
    tax_rate = db.Column(db.Float, nullable=True, default=0.0)  # percent
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    default_unit = db.Column(db.String(32), nullable=True)  # New column for default unit

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    address = db.Column(db.String(200))
    gstin = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bills = db.relationship('Bill', backref='customer', lazy=True)

class Bill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    customer_name = db.Column(db.String(100), nullable=False)
    mobile_number = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    gstin = db.Column(db.String(50), nullable=True)
    payment_mode = db.Column(db.String(50), nullable=True)
    invoice_number = db.Column(db.String(20), nullable=True)
    total_amount = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('BillItem', backref='bill', lazy=True)
    inventory_updated = db.Column(db.Boolean, default=False)

class BillItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bill_id = db.Column(db.Integer, db.ForeignKey('bill.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    tax_rate = db.Column(db.Float, nullable=True, default=0.0)
    unit = db.Column(db.String(32), nullable=True)  # New column for unit
    item = db.relationship('Item')

class Quotation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    customer_name = db.Column(db.String(100), nullable=False)
    mobile_number = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    gstin = db.Column(db.String(50), nullable=True)
    quotation_number = db.Column(db.String(20), nullable=True)
    total_amount = db.Column(db.Float, nullable=False)
    valid_until = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('QuotationItem', backref='quotation', lazy=True)
    customer = db.relationship('Customer', backref='quotations')

class QuotationItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quotation_id = db.Column(db.Integer, db.ForeignKey('quotation.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    tax_rate = db.Column(db.Float, nullable=True, default=0.0)
    item = db.relationship('Item')

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_name = db.Column(db.String(200), nullable=True)
    address = db.Column(db.String(300), nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    gstin = db.Column(db.String(50), nullable=True)
    website = db.Column(db.String(200), nullable=True)
    bank_name = db.Column(db.String(100), nullable=True)
    bank_account_number = db.Column(db.String(50), nullable=True)
    ifsc_code = db.Column(db.String(20), nullable=True)

class InventoryHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # 'edit', 'add', etc.
    old_values = db.Column(db.JSON)  # Store old values
    new_values = db.Column(db.JSON)  # Store new values
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    item = db.relationship('Item', backref='history')
    user = db.relationship('User', backref='inventory_history')

# Routes
@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
        
    items = Item.query.all()
    
    # Calculate statistics
    total_sales = db.session.query(db.func.sum(Bill.total_amount)).scalar() or 0
    total_customers = Customer.query.count()
    total_items = len(items)
    total_inventory_value = sum(item.price * item.stock for item in items)
    recent_bills = Bill.query.order_by(Bill.created_at.desc()).limit(5).all()
    
    # Additional statistics
    today = datetime.now().date()
    today_sales = db.session.query(db.func.sum(Bill.total_amount)).filter(
        db.func.date(Bill.created_at) == today
    ).scalar() or 0
    
    # Monthly sales
    current_month = datetime.now().month
    current_year = datetime.now().year
    monthly_sales = db.session.query(db.func.sum(Bill.total_amount)).filter(
        db.extract('month', Bill.created_at) == current_month,
        db.extract('year', Bill.created_at) == current_year
    ).scalar() or 0
    
    # Low stock items (less than 10 items)
    low_stock_items = Item.query.filter(Item.stock < 10).count()
    
    # Average bill amount
    avg_bill_amount = db.session.query(db.func.avg(Bill.total_amount)).scalar() or 0
    
    # Total bills count
    total_bills = Bill.query.count()
    
    return render_template('index.html', 
                         items=items,
                         total_sales=total_sales,
                         total_customers=total_customers,
                         total_items=total_items,
                         total_inventory_value=total_inventory_value,
                         recent_bills=recent_bills,
                         today_sales=today_sales,
                         monthly_sales=monthly_sales,
                         low_stock_items=low_stock_items,
                         avg_bill_amount=avg_bill_amount,
                         total_bills=total_bills)

@app.route('/add_item', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        hsn_sac_number = request.form['hsn_sac_number'] if request.form['hsn_sac_number'] else None
        tax_rate = float(request.form['tax_rate']) if request.form['tax_rate'] else 0.0
        # Handle default unit
        default_unit = request.form['default_unit']
        if default_unit == 'Other':
            default_unit = request.form['default_unit_other']
        new_item = Item(name=name, description=description, price=price, stock=stock, hsn_sac_number=hsn_sac_number, tax_rate=tax_rate, default_unit=default_unit)
        db.session.add(new_item)
        db.session.commit()
        flash('Item added successfully!')
        return redirect(url_for('index'))
    return render_template('add_item.html')

@app.route('/create_bill', methods=['GET', 'POST'])
@login_required
def create_bill():
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        if customer_id:
            customer = Customer.query.get(customer_id)
            customer_name = customer.name
            mobile_number = customer.phone
            email = customer.email
            address = customer.address
            gstin = customer.gstin
        else:
            # Handle walk-in customer
            customer_name = request.form.get('customer_name', '').strip()
            if not customer_name:
                customer_name = 'Walk-in Customer'
            mobile_number = request.form.get('mobile_number', '').strip() or None
            email = request.form.get('email', '').strip() or None
            address = request.form.get('address', '').strip() or None
            gstin = request.form.get('gstin', '').strip() or None
        payment_mode = request.form.get('payment_mode')
        items = request.form.getlist('items[]')
        quantities = request.form.getlist('quantities[]')
        units = request.form.getlist('units[]')
        unit_others = request.form.getlist('unit_others[]')
        
        # Check for stock availability before creating the bill
        for idx, (item_id, quantity) in enumerate(zip(items, quantities)):
            if int(quantity) > 0:
                item = Item.query.get(item_id)
                if item and int(quantity) > item.stock:
                    flash(f'Cannot bill more than available stock for item: {item.name} (Available: {item.stock}, Requested: {quantity})', 'danger')
                    return redirect(url_for('create_bill'))
        
        # Generate invoice number
        now = datetime.now()
        month_str = now.strftime('%Y-%m')
        count = Bill.query.filter(
            db.extract('year', Bill.created_at) == now.year,
            db.extract('month', Bill.created_at) == now.month
        ).count() + 1
        invoice_number = f"SQE-{now.year}-{now.month:02d}-{count}"
        
        subtotal = 0
        total_tax = 0
        total_amount = 0
        
        bill = Bill(
            customer_id=customer_id,
            customer_name=customer_name,
            mobile_number=mobile_number,
            email=email,
            address=address,
            gstin=gstin,
            payment_mode=payment_mode,
            invoice_number=invoice_number,
            total_amount=0
        )
        db.session.add(bill)
        
        for idx, (item_id, quantity) in enumerate(zip(items, quantities)):
            if int(quantity) > 0:
                item = Item.query.get(item_id)
                if item:
                    # Determine the unit
                    unit = units[idx] if units[idx] != 'Other' else unit_others[idx]
                    item_tax = item.tax_rate or 0.0
                    item_subtotal = item.price * int(quantity)
                    item_tax_amount = item_subtotal * (item_tax / 100)
                    subtotal += item_subtotal
                    total_tax += item_tax_amount
                    bill_item = BillItem(
                        bill=bill,
                        item=item,
                        quantity=int(quantity),
                        price=item.price,
                        tax_rate=item_tax,
                        unit=unit
                    )
                    db.session.add(bill_item)
        
        total_amount = subtotal + total_tax
        bill.total_amount = total_amount
        db.session.commit()

        # (REMOVED inventory update logic from here)

        flash('Bill created successfully!', 'success')
        return redirect(url_for('view_bills'))
    
    items = Item.query.all()
    customers = Customer.query.order_by(Customer.name).all()
    now = datetime.now()
    month_str = now.strftime('%Y%m')
    count = Bill.query.filter(
        db.extract('year', Bill.created_at) == now.year,
        db.extract('month', Bill.created_at) == now.month
    ).count() + 1
    invoice_number = f"{month_str}-{count:03d}"
    return render_template('create_bill.html', items=items, customers=customers, invoice_number=invoice_number, today=now.strftime('%d/%m/%Y'))

@app.route('/bills')
@login_required
def view_bills():
    bills = Bill.query.order_by(Bill.created_at.desc()).all()
    return render_template('bills.html', bills=bills)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        settings = Settings.query.first()
        if not settings:
            settings = Settings()
            db.session.add(settings)
        
        settings.company_name = request.form.get('company_name', '')
        settings.address = request.form.get('address', '')
        settings.phone = request.form.get('phone', '')
        settings.email = request.form.get('email', '')
        settings.gstin = request.form.get('gstin', '')
        settings.website = request.form.get('website', '')
        settings.bank_name = request.form.get('bank_name', '')
        settings.bank_account_number = request.form.get('bank_account_number', '')
        settings.ifsc_code = request.form.get('ifsc_code', '')
        
        db.session.commit()
        flash('Settings updated successfully!', 'success')
        return redirect(url_for('settings'))
    
    settings = Settings.query.first()
    return render_template('settings.html', settings=settings)

def generate_bill_pdf(bill, subtotal, total_tax):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, 
                           rightMargin=20, leftMargin=40, 
                           topMargin=8, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()
    
    # Color scheme to match example
    primary_color = colors.HexColor('#1A8CFF')    # Bright blue (matches example)
    secondary_color = colors.HexColor('#424242')  # Dark gray
    accent_color = colors.HexColor('#FF9900')     # Orange for totals (matches example)
    light_bg = colors.HexColor('#F5F5F5')         # Light gray background
    text_color = colors.HexColor('#212121')       # Near black for text
    
    # Create improved styles with better typography and color scheme
    styles.add(ParagraphStyle(
        name='CompanyHeader', fontSize=20, leading=24, alignment=1, 
        fontName='Helvetica', spaceAfter=4, textColor=primary_color))
    styles.add(ParagraphStyle(
        name='CompanySubHeader', fontSize=9, leading=11, alignment=0, 
        fontName='Helvetica', spaceAfter=1, textColor=secondary_color))
    styles.add(ParagraphStyle(
        name='NormalText', fontSize=8, leading=10, alignment=0, 
        fontName='Helvetica', textColor=text_color))
    styles.add(ParagraphStyle(
        name='TableHeader', fontSize=9, leading=11, alignment=1, 
        fontName='Helvetica', textColor=colors.white))
    styles.add(ParagraphStyle(
        name='TableCell', fontSize=8, leading=10, alignment=1, 
        fontName='Helvetica', textColor=text_color))
    styles.add(ParagraphStyle(
        name='Footer', fontSize=7, leading=9, alignment=1, 
        fontName='Helvetica', textColor=secondary_color))
    styles.add(ParagraphStyle(
        name='TotalAmount', fontSize=9, leading=11, alignment=2, 
        fontName='Helvetica', textColor=primary_color))
    styles.add(ParagraphStyle(
        name='BillTo', fontSize=9, leading=11, alignment=0, 
        fontName='Helvetica', textColor=primary_color))
    styles.add(ParagraphStyle(
        name='InvoiceInfo', fontSize=9, leading=11, alignment=0, 
        fontName='Helvetica', textColor=accent_color, 
        borderColor=accent_color, borderWidth=1, borderPadding=3))
    
    # Get company settings
    settings = Settings.query.first()
    
    # Add a decorative banner at the top
    top_banner = Table([['INVOICE']], colWidths=[540])
    top_banner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica'),
        ('FONTSIZE', (0, 0), (0, 0), 14),
        ('ALIGNMENT', (0, 0), (0, 0), 'CENTER'),
        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (0, 0), 4),
        ('BOTTOMPADDING', (0, 0), (0, 0), 4),
    ]))
    elements.append(top_banner)

    # Logo at the top left, immediately left of the company name, almost zero padding
    logo_path = os.path.join('static', 'logo.png')
    logo_data = None
    if os.path.exists(logo_path):
        img = Image(logo_path, width=40, height=40)
        logo_data = img
    else:
        logo_data = Paragraph("", styles['NormalText'])
    # Header row: logo and company name close together, minimal padding
    company_name = settings.company_name if settings and settings.company_name else ""
    company_name_para = Paragraph(company_name, ParagraphStyle(name='CenteredCompanyName', fontSize=14, leading=18, alignment=0, fontName='Helvetica-Bold', textColor=primary_color))
    # Center the logo and company name as a group
    logo_name_row = Table([[logo_data, company_name_para]], colWidths=[42, 200], hAlign='CENTER')
    logo_name_row.setStyle(TableStyle([
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (1, 0), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (1, 0), 0),
        ('RIGHTPADDING', (0, 0), (1, 0), 0),
        ('TOPPADDING', (0, 0), (1, 0), 0),
        ('BOTTOMPADDING', (0, 0), (1, 0), 0),
    ]))
    elements.append(logo_name_row)

    # Prepare customer details box (BILLED TO)
    customer_box_data = []
    customer_box_data.append([Paragraph("<b>BILLED TO:</b>", ParagraphStyle(name='BillToMedium', fontSize=12, leading=14, alignment=0, fontName='Helvetica-Bold', textColor=primary_color))])
    customer_name = bill.customer.name if bill.customer else bill.customer_name
    if customer_name:
        customer_box_data.append([Paragraph(f"<b>{customer_name}</b>", ParagraphStyle(name='CustomerMedium', fontSize=11, leading=13, alignment=0, fontName='Helvetica-Bold', textColor=text_color))])
    if bill.mobile_number:
        customer_box_data.append([Paragraph(f"Phone: {bill.mobile_number}", ParagraphStyle(name='CustomerMedium', fontSize=10, leading=12, alignment=0, fontName='Helvetica', textColor=text_color))])
    if bill.email:
        customer_box_data.append([Paragraph(f"Email: {bill.email}", ParagraphStyle(name='CustomerMedium', fontSize=10, leading=12, alignment=0, fontName='Helvetica', textColor=text_color))])
    if bill.address:
        customer_box_data.append([Paragraph(f"Address: {bill.address}", ParagraphStyle(name='CustomerMedium', fontSize=10, leading=12, alignment=0, fontName='Helvetica', textColor=text_color))])
    if bill.gstin:
        customer_box_data.append([Paragraph(f"GSTIN: {bill.gstin}", ParagraphStyle(name='CustomerMedium', fontSize=10, leading=12, alignment=0, fontName='Helvetica', textColor=text_color))])
    customer_box = Table(customer_box_data, colWidths=[180])
    customer_box.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, primary_color),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    # Company details box (already compact)
    company_details_content = []
    company_details_content.append(Paragraph("<b>SELLER'S DETAILS</b>", ParagraphStyle(name='SellerDetailsHeader', fontSize=11, leading=13, alignment=0, fontName='Helvetica-Bold', textColor=primary_color)))
    if settings:
        if settings.address:
            company_details_content.append(Paragraph(f"<b>Address:</b> {settings.address}", ParagraphStyle(name='CompanyDetailCompact', fontSize=9, leading=9, spaceAfter=0, fontName='Helvetica', textColor=secondary_color)))
        if settings.phone:
            company_details_content.append(Paragraph(f"<b>Tel:</b> {settings.phone}", ParagraphStyle(name='CompanyDetailCompact', fontSize=9, leading=9, spaceAfter=0, fontName='Helvetica', textColor=secondary_color)))
        if settings.email:
            company_details_content.append(Paragraph(f"<b>Email:</b> {settings.email}", ParagraphStyle(name='CompanyDetailCompact', fontSize=9, leading=9, spaceAfter=0, fontName='Helvetica', textColor=secondary_color)))
        if settings.gstin:
            company_details_content.append(Paragraph(f"<b>GSTIN:</b> {settings.gstin}", ParagraphStyle(name='CompanyDetailCompact', fontSize=9, leading=9, spaceAfter=0, fontName='Helvetica', textColor=secondary_color)))
        if settings.bank_name:
            company_details_content.append(Paragraph(f"<b>Bank Name:</b> {settings.bank_name}", ParagraphStyle(name='CompanyDetailCompact', fontSize=9, leading=9, spaceAfter=0, fontName='Helvetica', textColor=secondary_color)))
        if settings.bank_account_number:
            company_details_content.append(Paragraph(f"<b>Acc No:</b> {settings.bank_account_number}", ParagraphStyle(name='CompanyDetailCompact', fontSize=9, leading=9, spaceAfter=0, fontName='Helvetica', textColor=secondary_color)))
        if settings.ifsc_code:
            company_details_content.append(Paragraph(f"<b>IFSC:</b> {settings.ifsc_code}", ParagraphStyle(name='CompanyDetailCompact', fontSize=9, leading=9, spaceAfter=0, fontName='Helvetica', textColor=secondary_color)))
    company_details_data = [[detail] for detail in company_details_content]
    if not company_details_data:
        company_details_data = [[""]]
    company_details = Table(company_details_data, colWidths=[300])
    company_details.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (0, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1, primary_color),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    # Invoice info box (orange border)
    invoice_date = bill.created_at.strftime('%d/%m/%Y')
    invoice_number = bill.invoice_number
    invoice_data = [
        [Paragraph(f"<b>INVOICE #{invoice_number}</b>", ParagraphStyle(name='InvoiceLabel', fontSize=11, leading=13, alignment=0, fontName='Helvetica-Bold', textColor=accent_color))],
        [Paragraph(f"Date: {invoice_date}", styles['NormalText'])],
        [Paragraph(f"Payment Mode: {bill.payment_mode}", styles['NormalText'])]
    ]
    invoice_box = Table(invoice_data, colWidths=[300])
    invoice_box.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, accent_color),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    # Company details and invoice info stacked, as before
    stacked_boxes = Table([[company_details], [invoice_box]], colWidths=[300])
    stacked_boxes.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (0, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (0, 0), 0),
        ('BOTTOMPADDING', (0, 0), (0, 0), 2),
        ('TOPPADDING', (0, 1), (0, 1), 2),
        ('BOTTOMPADDING', (0, 1), (0, 1), 0),
    ]))

    # Place customer box left, stacked boxes right, both close to logo
    info_row = Table([[customer_box, stacked_boxes]], colWidths=[190, 320])
    info_row.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (1, 0), 'TOP'),
        ('LEFTPADDING', (0, 0), (1, 0), 0),
        ('RIGHTPADDING', (0, 0), (1, 0), 0),
        ('TOPPADDING', (0, 0), (1, 0), 0),
        ('BOTTOMPADDING', (0, 0), (1, 0), 0),
    ]))
    elements.append(info_row)
    elements.append(Spacer(1, 10))

    # Enhanced Items Table with styling that matches the example
    data = [
        [Paragraph('Item Description', styles['TableHeader']),
         Paragraph('HSN/SAC', styles['TableHeader']),
         Paragraph('Qty', styles['TableHeader']),
         Paragraph('Unit Price', styles['TableHeader']),
         Paragraph('Tax %', styles['TableHeader']),
         Paragraph('Tax Amt', styles['TableHeader']),
         Paragraph('Total', styles['TableHeader'])]
    ]
    
    # Alternate row colors for better readability
    row_colors = [light_bg, colors.white]
    row_style_list = [
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # Left align item description
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),  # Center align all other columns
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
    ]
    
    # Add row data with alternating colors
    for i, item in enumerate(bill.items):
        item_tax = item.tax_rate or 0
        tax_amount = item.price * item.quantity * item_tax / 100
        total = item.price * item.quantity + tax_amount
        
        # Add alternating row colors
        if i % 2 == 0:
            row_style_list.append(('BACKGROUND', (0, i+1), (-1, i+1), light_bg))
        
        # Removed the ■ symbol from the price display
        data.append([
            Paragraph(item.item.name, styles['TableCell']),
            Paragraph(item.item.hsn_sac_number or '', styles['TableCell']),
            Paragraph(str(item.quantity), styles['TableCell']),
            Paragraph(f"{item.price:.2f}", styles['TableCell']),
            Paragraph(f"{item_tax:.1f}%", styles['TableCell']),
            Paragraph(f"{tax_amount:.2f}", styles['TableCell']),
            Paragraph(f"{total:.2f}", styles['TableCell'])
        ])
    
    # Calculate total rows index
    total_row_index = len(data)
    
    # Add subtotal, tax and total rows matching the example - removed the ■ symbol
    data.extend([
        ['', '', '', '', '', Paragraph('Subtotal:', styles['TableCell']), Paragraph(f"{subtotal:.2f}", styles['TotalAmount'])],
        ['', '', '', '', '', Paragraph('Total Tax:', styles['TableCell']), Paragraph(f"{total_tax:.2f}", styles['TotalAmount'])],
        ['', '', '', '', '', Paragraph('TOTAL:', styles['TableHeader']), Paragraph(f"{bill.total_amount:.2f}", styles['TotalAmount'])]
    ])
    
    # Add styling for total rows
    row_style_list.extend([
        ('BACKGROUND', (5, total_row_index), (6, total_row_index), colors.white),
        ('BACKGROUND', (5, total_row_index+1), (6, total_row_index+1), colors.white),
        ('BACKGROUND', (5, total_row_index+2), (6, total_row_index+2), colors.white),
        ('TEXTCOLOR', (5, total_row_index+2), (5, total_row_index+2), text_color),
        ('TEXTCOLOR', (6, total_row_index+2), (6, total_row_index+2), text_color),
        ('SPAN', (0, total_row_index), (4, total_row_index)),
        ('SPAN', (0, total_row_index+1), (4, total_row_index+1)),
        ('SPAN', (0, total_row_index+2), (4, total_row_index+2)),
        ('ALIGN', (5, total_row_index), (5, total_row_index+2), 'RIGHT'),
        ('ALIGN', (6, total_row_index), (6, total_row_index+2), 'RIGHT'),
        ('LINEABOVE', (5, total_row_index), (6, total_row_index), 0.5, colors.black),
    ])
    
    # Create and style the table with more space - increased height
    # Adjust column widths to use more of the available space
    table = Table(data, colWidths=[150, 70, 50, 70, 50, 70, 120])
    table.setStyle(TableStyle(row_style_list + [
        # Add more height to each row
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),  # Reduced bottom padding
        ('TOPPADDING', (0, 1), (-1, -1), 6),     # Reduced top padding
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    # Terms and conditions in one compact line
    terms_text = "Terms & Conditions: 1. Goods once sold will not be taken back or exchanged. 2. Subject to local jurisdiction."
    
    terms = Paragraph(terms_text, 
                     ParagraphStyle(name='CompactTerms', 
                                   fontSize=6, 
                                   leading=7, 
                                   alignment=0, 
                                   fontName='Helvetica', 
                                   textColor=secondary_color,
                                   leftIndent=0,
                                   rightIndent=0,
                                   spaceBefore=0,
                                   spaceAfter=0,
                                   ))
    elements.append(terms)
    elements.append(Spacer(1, 1))
    
    # Thank you message matching the example
    thank_you = Table([
        [Paragraph("THANK YOU FOR YOUR BUSINESS!", 
                   ParagraphStyle(name='ThankYou', fontSize=10, alignment=1, 
                                 textColor=primary_color, fontName='Helvetica'))],
    ], colWidths=[540])
    
    thank_you.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(thank_you)
    
    # Very minimal footer
    elements.append(Spacer(1, 5))
    
    # Simple footer text centered with smaller font
    footer_text = "This is a computer generated invoice, no signature required."
    
    footer = Paragraph(footer_text, 
                      ParagraphStyle(name='MinimalFooter', 
                                    fontSize=6, 
                                    leading=8, 
                                    alignment=1, 
                                    fontName='Helvetica', 
                                    textColor=secondary_color))
    elements.append(footer)
    
    # Add Stamp & Signature box at the bottom right, flush with right margin
    elements.append(Spacer(1, 20))
    stamp_box = Table(
        [[Paragraph('<b>Stamp & Signature</b>', ParagraphStyle(name='StampLabel', fontSize=9, alignment=1, fontName='Helvetica'))],
         [""]],
        colWidths=[150], rowHeights=[15, 40]
    )
    stamp_box.setStyle(TableStyle([
        ('BOX', (0, 0), (0, 1), 1, colors.HexColor('#1A8CFF')),
        ('ALIGN', (0, 0), (0, 1), 'CENTER'),
        ('VALIGN', (0, 0), (0, 1), 'BOTTOM'),
        ('TOPPADDING', (0, 0), (0, 0), 2),
        ('BOTTOMPADDING', (0, 1), (0, 1), 10),
    ]))
    # Right align the box flush with the right margin
    elements.append(Table([["", stamp_box]], colWidths=[390, 150], hAlign='RIGHT'))
    
    # Build the PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

@app.route('/download_bill/<int:bill_id>')
def download_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    # Update inventory when downloading the bill
    if not bill.inventory_updated:
        for item in bill.items:
            db_item = Item.query.get(item.item_id)
            if db_item and db_item.stock >= item.quantity:
                db_item.stock -= item.quantity
        bill.inventory_updated = True
        db.session.commit()
    # Calculate totals
    subtotal = sum(item.price * item.quantity for item in bill.items)
    total_tax = sum(item.price * item.quantity * (item.tax_rate or 0) / 100 for item in bill.items)
    # Generate PDF in memory
    pdf_buffer = generate_bill_pdf(bill, subtotal, total_tax)
    # Send the PDF from memory
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'bill_{bill_id}.pdf'
    )

@app.route('/customers')
@login_required
def customers():
    customers = Customer.query.order_by(Customer.name).all()
    return render_template('customers.html', customers=customers)

@app.route('/add_customer', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        customer = Customer(
            name=request.form['name'],
            phone=request.form['phone'],
            email=request.form['email'],
            address=request.form['address'],
            gstin=request.form['gstin']
        )
        db.session.add(customer)
        db.session.commit()
        flash('Customer added successfully!', 'success')
        return redirect(url_for('customers'))
    return render_template('add_customer.html')

@app.route('/edit_customer/<int:id>', methods=['GET', 'POST'])
def edit_customer(id):
    customer = Customer.query.get_or_404(id)
    if request.method == 'POST':
        customer.name = request.form['name']
        customer.phone = request.form['phone']
        customer.email = request.form['email']
        customer.address = request.form['address']
        customer.gstin = request.form['gstin']
        db.session.commit()
        flash('Customer updated successfully!', 'success')
        return redirect(url_for('customers'))
    return render_template('edit_customer.html', customer=customer)

@app.route('/delete_customer/<int:id>')
def delete_customer(id):
    customer = Customer.query.get_or_404(id)
    if customer.bills:
        flash('Cannot delete customer with existing bills!', 'danger')
    else:
        db.session.delete(customer)
        db.session.commit()
        flash('Customer deleted successfully!', 'success')
    return redirect(url_for('customers'))

@app.route('/edit_item/<int:id>', methods=['GET', 'POST'])
def edit_item(id):
    if 'user_id' not in session:
        flash('Please login to edit items!', 'warning')
        return redirect(url_for('login'))
    item = Item.query.get_or_404(id)
    if request.method == 'POST':
        # Store old values
        old_values = {
            'name': item.name,
            'description': item.description,
            'price': item.price,
            'stock': item.stock,
            'hsn_sac_number': item.hsn_sac_number,
            'tax_rate': item.tax_rate,
            'default_unit': item.default_unit
        }
        # Update item
        item.name = request.form['name']
        item.description = request.form['description']
        item.price = float(request.form['price'])
        item.stock = int(request.form['stock'])
        item.hsn_sac_number = request.form['hsn_sac_number'] if request.form['hsn_sac_number'] else None
        item.tax_rate = float(request.form['tax_rate']) if request.form['tax_rate'] else 0.0
        # Handle default unit
        default_unit = request.form['default_unit']
        if default_unit == 'Other':
            default_unit = request.form['default_unit_other']
        item.default_unit = default_unit
        # Store new values
        new_values = {
            'name': item.name,
            'description': item.description,
            'price': item.price,
            'stock': item.stock,
            'hsn_sac_number': item.hsn_sac_number,
            'tax_rate': item.tax_rate,
            'default_unit': item.default_unit
        }
        # Create history entry
        history = InventoryHistory(
            item_id=item.id,
            user_id=session['user_id'],
            action='edit',
            old_values=old_values,
            new_values=new_values
        )
        db.session.add(history)
        db.session.commit()
        flash('Item updated successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('edit_item.html', item=item)

@app.route('/inventory_history')
@login_required
def inventory_history():
    history = InventoryHistory.query.order_by(InventoryHistory.created_at.desc()).all()
    return render_template('inventory_history.html', history=history)

@app.route('/quotations', methods=['GET', 'POST'])
@login_required
def quotations():
    if request.method == 'POST':
        # Check if new customer is being added
        new_customer_name = request.form.get('new_customer_name')
        if new_customer_name:
            new_customer = Customer(
                name=new_customer_name,
                phone=request.form.get('new_customer_phone'),
                email=request.form.get('new_customer_email'),
                address=request.form.get('new_customer_address'),
                gstin=request.form.get('new_customer_gstin')
            )
            db.session.add(new_customer)
            db.session.commit()
            customer_id = new_customer.id
        else:
            customer_id = request.form.get('customer_id')
            
        # Handle date format
        valid_until_str = request.form.get('valid_until')
        try:
            # Try DD/MM/YYYY format first
            valid_until = datetime.strptime(valid_until_str, '%d/%m/%Y')
        except ValueError:
            try:
                # Try YYYY-MM-DD format
                valid_until = datetime.strptime(valid_until_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format. Please use DD/MM/YYYY or YYYY-MM-DD', 'error')
                return redirect(url_for('quotations'))
        items = request.form.getlist('items[]')
        quantities = request.form.getlist('quantities[]')
        prices = request.form.getlist('prices[]')
        
        # Get customer details
        customer = Customer.query.get(customer_id)
        if customer:
            customer_name = customer.name
            mobile_number = customer.phone
            email = customer.email
            address = customer.address
            gstin = customer.gstin
        else:
            flash('Customer not found!', 'error')
            return redirect(url_for('quotations'))
        
        # Generate quotation number
        now = datetime.now()
        month_str = now.strftime('%Y%m')
        count = Quotation.query.filter(
            db.extract('year', Quotation.created_at) == now.year,
            db.extract('month', Quotation.created_at) == now.month
        ).count() + 1
        quotation_number = f"Q{month_str}-{count:03d}"
        
        # Calculate totals
        subtotal = 0
        total_tax = 0
        total_amount = 0
        
        # Create quotation
        quotation = Quotation(
            customer_id=customer_id,
            customer_name=customer_name,
            mobile_number=mobile_number,
            email=email,
            address=address,
            gstin=gstin,
            quotation_number=quotation_number,
            total_amount=0,
            valid_until=valid_until
        )
        db.session.add(quotation)
        
        # Add items
        for item_id, quantity, price in zip(items, quantities, prices):
            if not price or not quantity:
                continue  # Skip if price or quantity is empty
            if int(quantity) > 0:
                item = Item.query.get(item_id)
                if item:
                    item_tax = item.tax_rate or 0.0
                    item_subtotal = float(price) * int(quantity)
                    item_tax_amount = item_subtotal * (item_tax / 100)
                    subtotal += item_subtotal
                    total_tax += item_tax_amount
                    
                    quotation_item = QuotationItem(
                        quotation=quotation,
                        item=item,
                        quantity=int(quantity),
                        price=float(price),
                        tax_rate=item_tax
                    )
                    db.session.add(quotation_item)
        
        total_amount = subtotal + total_tax
        quotation.total_amount = total_amount
        db.session.commit()
        
        # Generate PDF
        pdf_buffer = generate_quotation_pdf(quotation, subtotal, total_tax)
        
        # Send the PDF
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'quotation_{quotation.id}.pdf'
        )
    
    customers = Customer.query.all()
    items = Item.query.all()
    return render_template('quotations.html', customers=customers, items=items)

def generate_quotation_pdf(quotation, subtotal, total_tax):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, 
                           rightMargin=20, leftMargin=40, 
                           topMargin=8, bottomMargin=20)
    elements = []
    styles = getSampleStyleSheet()
    
    # Color scheme to match example
    primary_color = colors.HexColor('#1A8CFF')    # Bright blue (matches example)
    secondary_color = colors.HexColor('#424242')  # Dark gray
    accent_color = colors.HexColor('#FF9900')     # Orange for totals (matches example)
    light_bg = colors.HexColor('#F5F5F5')         # Light gray background
    text_color = colors.HexColor('#212121')       # Near black for text
    
    # Create improved styles with better typography and color scheme
    styles.add(ParagraphStyle(
        name='CompanyHeader', fontSize=20, leading=24, alignment=1, 
        fontName='Helvetica', spaceAfter=4, textColor=primary_color))
    styles.add(ParagraphStyle(
        name='CompanySubHeader', fontSize=9, leading=11, alignment=0, 
        fontName='Helvetica', spaceAfter=1, textColor=secondary_color))
    styles.add(ParagraphStyle(
        name='NormalText', fontSize=8, leading=10, alignment=0, 
        fontName='Helvetica', textColor=text_color))
    styles.add(ParagraphStyle(
        name='TableHeader', fontSize=9, leading=11, alignment=1, 
        fontName='Helvetica', textColor=colors.white))
    styles.add(ParagraphStyle(
        name='TableCell', fontSize=8, leading=10, alignment=1, 
        fontName='Helvetica', textColor=text_color))
    styles.add(ParagraphStyle(
        name='Footer', fontSize=7, leading=9, alignment=1, 
        fontName='Helvetica', textColor=secondary_color))
    styles.add(ParagraphStyle(
        name='TotalAmount', fontSize=9, leading=11, alignment=2, 
        fontName='Helvetica', textColor=primary_color))
    styles.add(ParagraphStyle(
        name='BillTo', fontSize=9, leading=11, alignment=0, 
        fontName='Helvetica', textColor=primary_color))
    styles.add(ParagraphStyle(
        name='InvoiceInfo', fontSize=9, leading=11, alignment=0, 
        fontName='Helvetica', textColor=accent_color, 
        borderColor=accent_color, borderWidth=1, borderPadding=3))
    
    # Get company settings
    settings = Settings.query.first()
    
    # Add a decorative banner at the top
    top_banner = Table([['QUOTATION']], colWidths=[540])
    top_banner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), primary_color),
        ('TEXTCOLOR', (0, 0), (0, 0), colors.white),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica'),
        ('FONTSIZE', (0, 0), (0, 0), 14),
        ('ALIGNMENT', (0, 0), (0, 0), 'CENTER'),
        ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (0, 0), 4),
        ('BOTTOMPADDING', (0, 0), (0, 0), 4),
    ]))
    elements.append(top_banner)

    # Logo at the top left, immediately left of the company name, almost zero padding
    logo_path = os.path.join('static', 'logo.png')
    logo_data = None
    if os.path.exists(logo_path):
        img = Image(logo_path, width=40, height=40)
        logo_data = img
    else:
        logo_data = Paragraph("", styles['NormalText'])
    # Header row: logo and company name close together, minimal padding
    company_name = settings.company_name if settings and settings.company_name else ""
    company_name_para = Paragraph(company_name, ParagraphStyle(name='CenteredCompanyName', fontSize=14, leading=18, alignment=0, fontName='Helvetica-Bold', textColor=primary_color))
    # Center the logo and company name as a group
    logo_name_row = Table([[logo_data, company_name_para]], colWidths=[42, 200], hAlign='CENTER')
    logo_name_row.setStyle(TableStyle([
        ('ALIGN', (0, 0), (1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (1, 0), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (1, 0), 0),
        ('RIGHTPADDING', (0, 0), (1, 0), 0),
        ('TOPPADDING', (0, 0), (1, 0), 0),
        ('BOTTOMPADDING', (0, 0), (1, 0), 0),
    ]))
    elements.append(logo_name_row)

    # Prepare customer details box (QUOTED TO)
    customer_box_data = []
    customer_box_data.append([Paragraph("<b>QUOTED TO:</b>", ParagraphStyle(name='BillToMedium', fontSize=12, leading=14, alignment=0, fontName='Helvetica-Bold', textColor=primary_color))])
    customer_name = quotation.customer.name if quotation.customer else quotation.customer_name
    if customer_name:
        customer_box_data.append([Paragraph(f"<b>{customer_name}</b>", ParagraphStyle(name='CustomerMedium', fontSize=11, leading=13, alignment=0, fontName='Helvetica-Bold', textColor=text_color))])
    if quotation.mobile_number:
        customer_box_data.append([Paragraph(f"Phone: {quotation.mobile_number}", ParagraphStyle(name='CustomerMedium', fontSize=10, leading=12, alignment=0, fontName='Helvetica', textColor=text_color))])
    if quotation.email:
        customer_box_data.append([Paragraph(f"Email: {quotation.email}", ParagraphStyle(name='CustomerMedium', fontSize=10, leading=12, alignment=0, fontName='Helvetica', textColor=text_color))])
    if quotation.address:
        customer_box_data.append([Paragraph(f"Address: {quotation.address}", ParagraphStyle(name='CustomerMedium', fontSize=10, leading=12, alignment=0, fontName='Helvetica', textColor=text_color))])
    if quotation.gstin:
        customer_box_data.append([Paragraph(f"GSTIN: {quotation.gstin}", ParagraphStyle(name='CustomerMedium', fontSize=10, leading=12, alignment=0, fontName='Helvetica', textColor=text_color))])
    customer_box = Table(customer_box_data, colWidths=[180])
    customer_box.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, primary_color),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))

    # Company details box
    company_details_content = []
    company_details_content.append(Paragraph("<b>SELLER'S DETAILS</b>", ParagraphStyle(name='SellerDetailsHeader', fontSize=11, leading=13, alignment=0, fontName='Helvetica-Bold', textColor=primary_color)))
    if settings:
        if settings.address:
            company_details_content.append(Paragraph(f"<b>Address:</b> {settings.address}", ParagraphStyle(name='CompanyDetailCompact', fontSize=9, leading=9, spaceAfter=0, fontName='Helvetica', textColor=secondary_color)))
        if settings.phone:
            company_details_content.append(Paragraph(f"<b>Tel:</b> {settings.phone}", ParagraphStyle(name='CompanyDetailCompact', fontSize=9, leading=9, spaceAfter=0, fontName='Helvetica', textColor=secondary_color)))
        if settings.email:
            company_details_content.append(Paragraph(f"<b>Email:</b> {settings.email}", ParagraphStyle(name='CompanyDetailCompact', fontSize=9, leading=9, spaceAfter=0, fontName='Helvetica', textColor=secondary_color)))
        if settings.gstin:
            company_details_content.append(Paragraph(f"<b>GSTIN:</b> {settings.gstin}", ParagraphStyle(name='CompanyDetailCompact', fontSize=9, leading=9, spaceAfter=0, fontName='Helvetica', textColor=secondary_color)))
        if settings.bank_name:
            company_details_content.append(Paragraph(f"<b>Bank Name:</b> {settings.bank_name}", ParagraphStyle(name='CompanyDetailCompact', fontSize=9, leading=9, spaceAfter=0, fontName='Helvetica', textColor=secondary_color)))
        if settings.bank_account_number:
            company_details_content.append(Paragraph(f"<b>Acc No:</b> {settings.bank_account_number}", ParagraphStyle(name='CompanyDetailCompact', fontSize=9, leading=9, spaceAfter=0, fontName='Helvetica', textColor=secondary_color)))
        if settings.ifsc_code:
            company_details_content.append(Paragraph(f"<b>IFSC:</b> {settings.ifsc_code}", ParagraphStyle(name='CompanyDetailCompact', fontSize=9, leading=9, spaceAfter=0, fontName='Helvetica', textColor=secondary_color)))
    company_details_data = [[detail] for detail in company_details_content]
    if not company_details_data:
        company_details_data = [[""]]
    company_details = Table(company_details_data, colWidths=[300])
    company_details.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (0, -1), 'MIDDLE'),
        ('BOX', (0, 0), (-1, -1), 1, primary_color),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    # Quotation info box (orange border)
    quotation_date = quotation.created_at.strftime('%d/%m/%Y')
    quotation_number = quotation.quotation_number
    valid_until = quotation.valid_until.strftime('%d/%m/%Y')
    quotation_data = [
        [Paragraph(f"<b>QUOTATION #{quotation_number}</b>", ParagraphStyle(name='InvoiceLabel', fontSize=11, leading=13, alignment=0, fontName='Helvetica-Bold', textColor=accent_color))],
        [Paragraph(f"Date: {quotation_date}", styles['NormalText'])],
        [Paragraph(f"Valid Until: {valid_until}", styles['NormalText'])]
    ]
    quotation_box = Table(quotation_data, colWidths=[300])
    quotation_box.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1, accent_color),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))

    # Company details and quotation info stacked
    stacked_boxes = Table([[company_details], [quotation_box]], colWidths=[300])
    stacked_boxes.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (0, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (0, 0), 0),
        ('BOTTOMPADDING', (0, 0), (0, 0), 2),
        ('TOPPADDING', (0, 1), (0, 1), 2),
        ('BOTTOMPADDING', (0, 1), (0, 1), 0),
    ]))

    # Place customer box left, stacked boxes right
    info_row = Table([[customer_box, stacked_boxes]], colWidths=[190, 320])
    info_row.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (1, 0), 'TOP'),
        ('LEFTPADDING', (0, 0), (1, 0), 0),
        ('RIGHTPADDING', (0, 0), (1, 0), 0),
        ('TOPPADDING', (0, 0), (1, 0), 0),
        ('BOTTOMPADDING', (0, 0), (1, 0), 0),
    ]))
    elements.append(info_row)
    elements.append(Spacer(1, 10))

    # Enhanced Items Table with styling that matches the example
    data = [
        [Paragraph('Item Description', styles['TableHeader']),
         Paragraph('HSN/SAC', styles['TableHeader']),
         Paragraph('Qty', styles['TableHeader']),
         Paragraph('Unit Price', styles['TableHeader']),
         Paragraph('Tax %', styles['TableHeader']),
         Paragraph('Tax Amt', styles['TableHeader']),
         Paragraph('Total', styles['TableHeader'])]
    ]
    
    # Alternate row colors for better readability
    row_colors = [light_bg, colors.white]
    row_style_list = [
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # Left align item description
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),  # Center align all other columns
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
    ]
    
    # Add row data with alternating colors
    for i, item in enumerate(quotation.items):
        item_tax = item.tax_rate or 0
        tax_amount = item.price * item.quantity * item_tax / 100
        total = item.price * item.quantity + tax_amount
        
        # Add alternating row colors
        if i % 2 == 0:
            row_style_list.append(('BACKGROUND', (0, i+1), (-1, i+1), light_bg))
        
        data.append([
            Paragraph(item.item.name, styles['TableCell']),
            Paragraph(item.item.hsn_sac_number or '', styles['TableCell']),
            Paragraph(str(item.quantity), styles['TableCell']),
            Paragraph(f"{item.price:.2f}", styles['TableCell']),
            Paragraph(f"{item_tax:.1f}%", styles['TableCell']),
            Paragraph(f"{tax_amount:.2f}", styles['TableCell']),
            Paragraph(f"{total:.2f}", styles['TableCell'])
        ])
    
    # Calculate total rows index
    total_row_index = len(data)
    
    # Add subtotal, tax and total rows matching the example
    data.extend([
        ['', '', '', '', '', Paragraph('Subtotal:', styles['TableCell']), Paragraph(f"{subtotal:.2f}", styles['TotalAmount'])],
        ['', '', '', '', '', Paragraph('Total Tax:', styles['TableCell']), Paragraph(f"{total_tax:.2f}", styles['TotalAmount'])],
        ['', '', '', '', '', Paragraph('TOTAL:', styles['TableHeader']), Paragraph(f"{quotation.total_amount:.2f}", styles['TotalAmount'])]
    ])
    
    # Add styling for total rows
    row_style_list.extend([
        ('BACKGROUND', (5, total_row_index), (6, total_row_index), colors.white),
        ('BACKGROUND', (5, total_row_index+1), (6, total_row_index+1), colors.white),
        ('BACKGROUND', (5, total_row_index+2), (6, total_row_index+2), colors.white),
        ('TEXTCOLOR', (5, total_row_index+2), (5, total_row_index+2), text_color),
        ('TEXTCOLOR', (6, total_row_index+2), (6, total_row_index+2), text_color),
        ('SPAN', (0, total_row_index), (4, total_row_index)),
        ('SPAN', (0, total_row_index+1), (4, total_row_index+1)),
        ('SPAN', (0, total_row_index+2), (4, total_row_index+2)),
        ('ALIGN', (5, total_row_index), (5, total_row_index+2), 'RIGHT'),
        ('ALIGN', (6, total_row_index), (6, total_row_index+2), 'RIGHT'),
        ('LINEABOVE', (5, total_row_index), (6, total_row_index), 0.5, colors.black),
    ])
    
    # Create and style the table with more space
    table = Table(data, colWidths=[150, 70, 50, 70, 50, 70, 120])
    table.setStyle(TableStyle(row_style_list + [
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))
    
    # Terms and conditions in one compact line
    terms_text = "Terms & Conditions: 1. This quotation is valid until the specified date. 2. Prices are subject to change without notice. 3. All prices are exclusive of taxes unless specified. 4. Payment terms to be discussed. 5. Subject to local jurisdiction. 6. E. & O.E."
    
    terms = Paragraph(terms_text, 
                     ParagraphStyle(name='CompactTerms', 
                                   fontSize=6, 
                                   leading=7, 
                                   alignment=0, 
                                   fontName='Helvetica', 
                                   textColor=secondary_color,
                                   leftIndent=0,
                                   rightIndent=0,
                                   spaceBefore=0,
                                   spaceAfter=0,
                                   ))
    elements.append(terms)
    elements.append(Spacer(1, 1))
    
    # Thank you message
    thank_you = Table([
        [Paragraph("THANK YOU FOR YOUR BUSINESS!", 
                   ParagraphStyle(name='ThankYou', fontSize=10, alignment=1, 
                                 textColor=primary_color, fontName='Helvetica'))],
    ], colWidths=[540])
    
    thank_you.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(thank_you)
    
    # Very minimal footer
    elements.append(Spacer(1, 5))
    
    # Simple footer text centered with smaller font
    footer_text = "This is a computer generated quotation, no signature required."
    
    footer = Paragraph(footer_text, 
                      ParagraphStyle(name='MinimalFooter', 
                                    fontSize=6, 
                                    leading=8, 
                                    alignment=1, 
                                    fontName='Helvetica', 
                                    textColor=secondary_color))
    elements.append(footer)
    
    # Build the PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer

@app.route('/api/product_sales/<int:product_id>')
def product_sales(product_id):
    # Get all bill items for this product
    sales = db.session.query(
        BillItem,
        Bill,
        Customer
    ).join(
        Bill, BillItem.bill_id == Bill.id
    ).outerjoin(
        Customer, Bill.customer_id == Customer.id
    ).filter(
        BillItem.item_id == product_id
    ).order_by(
        Bill.created_at.desc()
    ).all()
    
    sales_data = []
    for bill_item, bill, customer in sales:
        sales_data.append({
            'date': bill.created_at.isoformat(),
            'invoice_number': bill.invoice_number,
            'customer_name': customer.name if customer else bill.customer_name,
            'quantity': bill_item.quantity,
            'price': bill_item.price,
            'total': bill_item.quantity * bill_item.price
        })
    
    return jsonify(sales_data)

@app.route('/export/bills')
def export_bills():
    import csv
    from io import StringIO
    bills = Bill.query.order_by(Bill.created_at.desc()).all()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Invoice Number', 'Customer Name', 'Date', 'Total Amount', 'Payment Mode'])
    for bill in bills:
        cw.writerow([
            bill.invoice_number,
            bill.customer_name,
            bill.created_at.strftime('%Y-%m-%d %H:%M'),
            bill.total_amount,
            bill.payment_mode
        ])
    output = si.getvalue()
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=bills.csv"})

@app.route('/export/customers')
def export_customers():
    import csv
    from io import StringIO
    customers = Customer.query.order_by(Customer.name).all()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Name', 'Phone', 'Email', 'Address', 'GSTIN', 'Created At'])
    for c in customers:
        cw.writerow([
            c.name,
            c.phone,
            c.email,
            c.address,
            c.gstin,
            c.created_at.strftime('%Y-%m-%d %H:%M')
        ])
    output = si.getvalue()
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=customers.csv"})

@app.route('/export/inventory')
def export_inventory():
    import csv
    from io import StringIO
    items = Item.query.order_by(Item.name).all()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Name', 'Description', 'Price', 'Stock', 'HSN/SAC Number', 'Tax Rate', 'Created At'])
    for item in items:
        cw.writerow([
            item.name,
            item.description,
            item.price,
            item.stock,
            item.hsn_sac_number,
            item.tax_rate,
            item.created_at.strftime('%Y-%m-%d %H:%M')
        ])
    output = si.getvalue()
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=inventory.csv"})

@app.route('/view_bill/<int:bill_id>')
def view_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    # Calculate subtotal and total tax
    subtotal = sum(item.price * item.quantity for item in bill.items)
    total_tax = sum(item.price * item.quantity * (item.tax_rate or 0) / 100 for item in bill.items)
    settings = Settings.query.first()
    return render_template('view_bill.html', bill=bill, subtotal=subtotal, total_tax=total_tax, settings=settings)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('index')
            return redirect(next_page)
        else:
            flash('Invalid username or password!', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/reset_db')
@login_required
def reset_db():
    if current_user.role != 'admin':
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    # Clear all data from all tables except User
    for table in reversed(db.metadata.sorted_tables):
        if table.name != 'user':
            db.session.execute(table.delete())
    db.session.commit()
    flash('Database cleared successfully!', 'success')
    return redirect(url_for('index'))

def recreate_database():
    with app.app_context():
        # Drop all tables
        db.drop_all()
        # Create all tables
        db.create_all()
        # Create admin user if none exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')  # Change this password in production!
            db.session.add(admin)
            db.session.commit()
            print("Admin user created!")

@app.route('/delete_bill/<int:id>', methods=['POST'])
@login_required
def delete_bill(id):
    bill = Bill.query.get_or_404(id)
    # Delete all bill items first
    for item in bill.items:
        db.session.delete(item)
    db.session.delete(bill)
    db.session.commit()
    flash('Bill deleted successfully!', 'success')
    return redirect(url_for('view_bills'))

@app.route('/delete_item/<int:id>', methods=['POST'])
@login_required
def delete_item(id):
    item = Item.query.get_or_404(id)
    # Delete all related inventory history records
    for history in item.history:
        db.session.delete(history)
    db.session.delete(item)
    db.session.commit()
    flash('Item deleted successfully!', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    recreate_database()
    app.run(debug=True, host='0.0.0.0', port=5001) 