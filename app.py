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
from io import BytesIO
from reportlab.graphics.barcode import createBarcodeDrawing
from reportlab.graphics.shapes import Drawing
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Production-ready configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///erp.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Database Models
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    hsn_sac_number = db.Column(db.String(20), nullable=True)
    tax_rate = db.Column(db.Float, nullable=True, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=True)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    tax_rate = db.Column(db.Float, nullable=True, default=0.0)
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
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=True)
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
    user_id = db.Column(db.Integer, nullable=True)
    action = db.Column(db.String(50), nullable=False)
    old_values = db.Column(db.Text)
    new_values = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    item = db.relationship('Item', backref='history')

@app.route('/')
def index():
    items = Item.query.order_by(Item.name).all()
    
    # Calculate total sales
    total_sales = db.session.query(db.func.sum(Bill.total_amount)).scalar() or 0
    
    # Calculate today's sales
    today = datetime.utcnow().date()
    today_sales = db.session.query(db.func.sum(Bill.total_amount))\
        .filter(db.func.date(Bill.created_at) == today).scalar() or 0
    
    # Calculate monthly sales
    first_day = today.replace(day=1)
    monthly_sales = db.session.query(db.func.sum(Bill.total_amount))\
        .filter(db.func.date(Bill.created_at) >= first_day).scalar() or 0
    
    # Calculate average bill amount
    total_bills = Bill.query.count()
    avg_bill_amount = total_sales / total_bills if total_bills > 0 else 0
    
    # Get total customers
    total_customers = Customer.query.count()
    
    # Get total bills count
    total_bills = Bill.query.count()
    
    # Count low stock items (less than 10)
    low_stock_items = Item.query.filter(Item.stock < 10).count()
    
    # Calculate total inventory value
    total_inventory_value = db.session.query(db.func.sum(Item.price * Item.stock)).scalar() or 0
    
    # Get recent bills
    recent_bills = Bill.query.order_by(Bill.created_at.desc()).limit(5).all()
    
    return render_template('index.html',
                         items=items,
                         total_sales=total_sales,
                         today_sales=today_sales,
                         monthly_sales=monthly_sales,
                         avg_bill_amount=avg_bill_amount,
                         total_customers=total_customers,
                         total_bills=total_bills,
                         low_stock_items=low_stock_items,
                         total_inventory_value=total_inventory_value,
                         recent_bills=recent_bills)

@app.route('/add_item', methods=['GET', 'POST'])
def add_item():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        hsn_sac_number = request.form['hsn_sac_number'] if request.form['hsn_sac_number'] else None
        tax_rate = float(request.form['tax_rate']) if request.form['tax_rate'] else 0.0
        new_item = Item(name=name, description=description, price=price, stock=stock, hsn_sac_number=hsn_sac_number, tax_rate=tax_rate)
        db.session.add(new_item)
        db.session.commit()
        flash('Item added successfully!')
        return redirect(url_for('index'))
    return render_template('add_item.html')

@app.route('/create_bill', methods=['GET', 'POST'])
def create_bill():
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        if not customer_id:
            flash('Please select a customer', 'danger')
            return redirect(url_for('create_bill'))
            
        customer = Customer.query.get(customer_id)
        if not customer:
            flash('Customer not found', 'danger')
            return redirect(url_for('create_bill'))
            
        customer_name = customer.name
        mobile_number = customer.phone
        email = customer.email
        address = customer.address
        gstin = customer.gstin
        payment_mode = request.form.get('payment_mode')
        items = request.form.getlist('items[]')
        quantities = request.form.getlist('quantities[]')
        
        for item_id, quantity in zip(items, quantities):
            if int(quantity) > 0:
                item = Item.query.get(item_id)
                if item and int(quantity) > item.stock:
                    flash(f'Insufficient stock for {item.name}. Available: {item.stock}, Requested: {quantity}', 'danger')
                    return redirect(url_for('create_bill'))
        
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
        
        for item_id, quantity in zip(items, quantities):
            if int(quantity) > 0:
                item = Item.query.get(item_id)
                if item:
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
                        tax_rate=item_tax
                    )
                    db.session.add(bill_item)
                    item.stock -= int(quantity)
        
        total_amount = subtotal + total_tax
        bill.total_amount = total_amount
        db.session.commit()

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
def view_bills():
    bills = Bill.query.order_by(Bill.created_at.desc()).all()
    return render_template('bills.html', bills=bills)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
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
    
    primary_color = colors.HexColor('#1A8CFF')
    secondary_color = colors.HexColor('#424242')
    accent_color = colors.HexColor('#FF9900')
    light_bg = colors.HexColor('#F5F5F5')
    text_color = colors.HexColor('#212121')
    
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
    
    settings = Settings.query.first()
    
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

    logo_path = os.path.join('static', 'logo.png')
    logo_data = None
    if os.path.exists(logo_path):
        img = Image(logo_path, width=40, height=40)
        logo_data = img
    else:
        logo_data = Paragraph("", styles['NormalText'])
    company_name = settings.company_name if settings and settings.company_name else ""
    company_name_para = Paragraph(company_name, ParagraphStyle(name='CenteredCompanyName', fontSize=14, leading=18, alignment=0, fontName='Helvetica-Bold', textColor=primary_color))
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

    stacked_boxes = Table([[company_details], [invoice_box]], colWidths=[300])
    stacked_boxes.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (0, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (0, 0), 0),
        ('BOTTOMPADDING', (0, 0), (0, 0), 2),
        ('TOPPADDING', (0, 1), (0, 1), 2),
        ('BOTTOMPADDING', (0, 1), (0, 1), 0),
    ]))

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

    data = [
        [Paragraph('Item Description', styles['TableHeader']),
         Paragraph('HSN/SAC', styles['TableHeader']),
         Paragraph('Qty', styles['TableHeader']),
         Paragraph('Unit Price', styles['TableHeader']),
         Paragraph('Tax %', styles['TableHeader']),
         Paragraph('Tax Amt', styles['TableHeader']),
         Paragraph('Total', styles['TableHeader'])]
    ]
    
    row_colors = [light_bg, colors.white]
    row_style_list = [
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
    ]
    
    for i, item in enumerate(bill.items):
        item_tax = item.tax_rate or 0
        tax_amount = item.price * item.quantity * item_tax / 100
        total = item.price * item.quantity + tax_amount
        
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
    
    total_row_index = len(data)
    
    data.extend([
        ['', '', '', '', '', Paragraph('Subtotal:', styles['TableCell']), Paragraph(f"{subtotal:.2f}", styles['TotalAmount'])],
        ['', '', '', '', '', Paragraph('Total Tax:', styles['TableCell']), Paragraph(f"{total_tax:.2f}", styles['TotalAmount'])],
        ['', '', '', '', '', Paragraph('TOTAL:', styles['TableHeader']), Paragraph(f"{bill.total_amount:.2f}", styles['TotalAmount'])]
    ])
    
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
    
    table = Table(data, colWidths=[150, 70, 50, 70, 50, 70, 120])
    table.setStyle(TableStyle(row_style_list + [
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))
    
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
    
    elements.append(Spacer(1, 5))
    
    footer_text = "This is a computer generated invoice, no signature required."
    
    footer = Paragraph(footer_text, 
                      ParagraphStyle(name='MinimalFooter', 
                                    fontSize=6, 
                                    leading=8, 
                                    alignment=1, 
                                    fontName='Helvetica', 
                                    textColor=secondary_color))
    elements.append(footer)
    
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
    elements.append(Table([["", stamp_box]], colWidths=[390, 150], hAlign='RIGHT'))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

@app.route('/download_bill/<int:bill_id>')
def download_bill(bill_id):
    bill = Bill.query.get_or_404(bill_id)
    if not bill.inventory_updated:
        for item in bill.items:
            db_item = Item.query.get(item.item_id)
            if db_item and db_item.stock >= item.quantity:
                db_item.stock -= item.quantity
        bill.inventory_updated = True
        db.session.commit()
    subtotal = sum(item.price * item.quantity for item in bill.items)
    total_tax = sum(item.price * item.quantity * (item.tax_rate or 0) / 100 for item in bill.items)
    pdf_buffer = generate_bill_pdf(bill, subtotal, total_tax)
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'bill_{bill_id}.pdf'
    )

@app.route('/customers')
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
    item = Item.query.get(id)
    if not item:
        flash('Item not found.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            old_values = {
                'name': item.name,
                'description': item.description,
                'price': item.price,
                'stock': item.stock,
                'hsn_sac_number': item.hsn_sac_number,
                'tax_rate': item.tax_rate
            }
            
            item.name = request.form['name']
            item.description = request.form['description']
            item.price = float(request.form['price'])
            item.stock = int(request.form['stock'])
            item.hsn_sac_number = request.form['hsn_sac_number']
            item.tax_rate = float(request.form['tax_rate'])
            
            new_values = {
                'name': item.name,
                'description': item.description,
                'price': item.price,
                'stock': item.stock,
                'hsn_sac_number': item.hsn_sac_number,
                'tax_rate': item.tax_rate
            }
            
            # Create inventory history entry without user_id
            history = InventoryHistory(
                item_id=item.id,
                action='edit',
                old_values=json.dumps(old_values),
                new_values=json.dumps(new_values),
                created_at=datetime.utcnow(),
                user_id=None  # Explicitly set user_id to None
            )
            db.session.add(history)
            
            db.session.commit()
            flash('Item updated successfully!', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating item: {str(e)}', 'error')
            return redirect(url_for('edit_item', id=id))
    
    return render_template('edit_item.html', item=item)

@app.route('/inventory_history')
def inventory_history():
    history = InventoryHistory.query.order_by(InventoryHistory.created_at.desc()).all()
    for entry in history:
        entry.old_values_dict = json.loads(entry.old_values) if isinstance(entry.old_values, str) else entry.old_values
        entry.new_values_dict = json.loads(entry.new_values) if isinstance(entry.new_values, str) else entry.new_values
    return render_template('inventory_history.html', history=history)

@app.route('/quotations', methods=['GET', 'POST'])
def quotations():
    if request.method == 'POST':
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
            
        valid_until_str = request.form.get('valid_until')
        try:
            valid_until = datetime.strptime(valid_until_str, '%d/%m/%Y')
        except ValueError:
            try:
                valid_until = datetime.strptime(valid_until_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format. Please use DD/MM/YYYY or YYYY-MM-DD', 'error')
                return redirect(url_for('quotations'))
        items = request.form.getlist('items[]')
        quantities = request.form.getlist('quantities[]')
        prices = request.form.getlist('prices[]')
        
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
        
        now = datetime.now()
        month_str = now.strftime('%Y%m')
        count = Quotation.query.filter(
            db.extract('year', Quotation.created_at) == now.year,
            db.extract('month', Quotation.created_at) == now.month
        ).count() + 1
        quotation_number = f"Q{month_str}-{count:03d}"
        
        subtotal = 0
        total_tax = 0
        total_amount = 0
        
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
        
        for item_id, quantity, price in zip(items, quantities, prices):
            if not price or not quantity:
                continue
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
        
        pdf_buffer = generate_quotation_pdf(quotation, subtotal, total_tax)
        
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
    
    primary_color = colors.HexColor('#1A8CFF')
    secondary_color = colors.HexColor('#424242')
    accent_color = colors.HexColor('#FF9900')
    light_bg = colors.HexColor('#F5F5F5')
    text_color = colors.HexColor('#212121')
    
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
    
    settings = Settings.query.first()
    
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

    logo_path = os.path.join('static', 'logo.png')
    logo_data = None
    if os.path.exists(logo_path):
        img = Image(logo_path, width=40, height=40)
        logo_data = img
    else:
        logo_data = Paragraph("", styles['NormalText'])
    company_name = settings.company_name if settings and settings.company_name else ""
    company_name_para = Paragraph(company_name, ParagraphStyle(name='CenteredCompanyName', fontSize=14, leading=18, alignment=0, fontName='Helvetica-Bold', textColor=primary_color))
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

    stacked_boxes = Table([[company_details], [quotation_box]], colWidths=[300])
    stacked_boxes.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (0, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (0, 0), 0),
        ('BOTTOMPADDING', (0, 0), (0, 0), 2),
        ('TOPPADDING', (0, 1), (0, 1), 2),
        ('BOTTOMPADDING', (0, 1), (0, 1), 0),
    ]))

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

    data = [
        [Paragraph('Item Description', styles['TableHeader']),
         Paragraph('HSN/SAC', styles['TableHeader']),
         Paragraph('Qty', styles['TableHeader']),
         Paragraph('Unit Price', styles['TableHeader']),
         Paragraph('Tax %', styles['TableHeader']),
         Paragraph('Tax Amt', styles['TableHeader']),
         Paragraph('Total', styles['TableHeader'])]
    ]
    
    row_colors = [light_bg, colors.white]
    row_style_list = [
        ('BACKGROUND', (0, 0), (-1, 0), primary_color),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
    ]
    
    for i, item in enumerate(quotation.items):
        item_tax = item.tax_rate or 0
        tax_amount = item.price * item.quantity * item_tax / 100
        total = item.price * item.quantity + tax_amount
        
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
    
    total_row_index = len(data)
    
    data.extend([
        ['', '', '', '', '', Paragraph('Subtotal:', styles['TableCell']), Paragraph(f"{subtotal:.2f}", styles['TotalAmount'])],
        ['', '', '', '', '', Paragraph('Total Tax:', styles['TableCell']), Paragraph(f"{total_tax:.2f}", styles['TotalAmount'])],
        ['', '', '', '', '', Paragraph('TOTAL:', styles['TableHeader']), Paragraph(f"{quotation.total_amount:.2f}", styles['TotalAmount'])]
    ])
    
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
    
    table = Table(data, colWidths=[150, 70, 50, 70, 50, 70, 120])
    table.setStyle(TableStyle(row_style_list + [
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))
    
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
    
    elements.append(Spacer(1, 5))
    
    footer_text = "This is a computer generated quotation, no signature required."
    
    footer = Paragraph(footer_text, 
                      ParagraphStyle(name='MinimalFooter', 
                                    fontSize=6, 
                                    leading=8, 
                                    alignment=1, 
                                    fontName='Helvetica', 
                                    textColor=secondary_color))
    elements.append(footer)
    
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
    elements.append(Table([["", stamp_box]], colWidths=[390, 150], hAlign='RIGHT'))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

@app.route('/api/product_sales/<int:product_id>')
def product_sales(product_id):
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
    subtotal = sum(item.price * item.quantity for item in bill.items)
    total_tax = sum(item.price * item.quantity * (item.tax_rate or 0) / 100 for item in bill.items)
    settings = Settings.query.first()
    return render_template('view_bill.html', bill=bill, subtotal=subtotal, total_tax=total_tax, settings=settings)

@app.route('/delete_bill/<int:id>', methods=['POST'])
def delete_bill(id):
    try:
        bill = Bill.query.get(id)
        if not bill:
            flash('Bill not found!', 'danger')
            return redirect(url_for('view_bills'))
            
        # Check if bill has been downloaded/generated
        if bill.inventory_updated:
            flash('Cannot delete bill that has already been processed!', 'danger')
            return redirect(url_for('view_bills'))
            
        # Restore item stock
        for bill_item in bill.items:
            item = Item.query.get(bill_item.item_id)
            if item:
                item.stock += bill_item.quantity
            else:
                flash(f'Warning: Item ID {bill_item.item_id} not found while restoring stock', 'warning')
                
        # Delete bill items and bill
        for item in bill.items:
            db.session.delete(item)
        db.session.delete(bill)
        db.session.commit()
        flash('Bill deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting bill: {str(e)}', 'danger')
        
    return redirect(url_for('view_bills'))

@app.route('/delete_item/<int:id>', methods=['POST'])
def delete_item(id):
    try:
        item = Item.query.get(id)
        if not item:
            flash('Item not found!', 'danger')
            return redirect(url_for('index'))
            
        # Check if item is used in any bills
        bill_items = BillItem.query.filter_by(item_id=id).first()
        if bill_items:
            flash('Cannot delete item as it is associated with existing bills!', 'danger')
            return redirect(url_for('index'))
            
        # Check if item is used in any quotations
        quotation_items = QuotationItem.query.filter_by(item_id=id).first()
        if quotation_items:
            flash('Cannot delete item as it is associated with existing quotations!', 'danger')
            return redirect(url_for('index'))
            
        # Check if item has any inventory history
        history = InventoryHistory.query.filter_by(item_id=id).first()
        if history:
            flash('Cannot delete item as it has inventory history!', 'danger')
            return redirect(url_for('index'))
            
        db.session.delete(item)
        db.session.commit()
        flash('Item deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting item: {str(e)}', 'danger')
        
    return redirect(url_for('index'))

@app.route('/force_delete_item/<int:id>', methods=['POST'])
def force_delete_item(id):
    try:
        item = Item.query.get(id)
        if not item:
            flash('Item not found!', 'danger')
            return redirect(url_for('index'))
        # Set item_id to NULL in BillItem, QuotationItem, and InventoryHistory
        BillItem.query.filter_by(item_id=id).update({BillItem.item_id: None})
        QuotationItem.query.filter_by(item_id=id).update({QuotationItem.item_id: None})
        InventoryHistory.query.filter_by(item_id=id).update({InventoryHistory.item_id: None})
        db.session.delete(item)
        db.session.commit()
        flash('Item force deleted. Related records will show "Not Available".', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Error force deleting item: {str(e)}', 'danger')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5001) 