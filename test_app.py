import pytest
from app import app, db, Item, Customer

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
        yield client

def test_force_delete_item_and_references(client):
    # Add a customer
    client.post('/add_customer', data={
        'name': 'Test Customer',
        'phone': '1234567890',
        'email': 'test@example.com',
        'address': '123 Test St',
        'gstin': 'GST123'
    }, follow_redirects=True)

    # Add an item
    client.post('/add_item', data={
        'name': 'Test Item',
        'description': 'A test item',
        'price': 100,
        'stock': 10,
        'hsn_sac_number': '1234',
        'tax_rate': 18
    }, follow_redirects=True)

    # Get customer and item IDs
    customer = Customer.query.first()
    item = Item.query.first()

    # Create a bill with the item and customer
    client.post('/create_bill', data={
        'customer_id': customer.id,
        'payment_mode': 'Cash',
        'items[]': [str(item.id)],
        'quantities[]': ['2']
    }, follow_redirects=True)

    # Create a quotation with the item and customer
    client.post('/quotations', data={
        'customer_id': customer.id,
        'valid_until': '2099-12-31',
        'items[]': [str(item.id)],
        'quantities[]': ['1'],
        'prices[]': ['100']
    }, follow_redirects=True)

    # Force delete the item
    response = client.post(f'/force_delete_item/{item.id}', follow_redirects=True)
    print(response.data.decode())
    assert b'Item force deleted' in response.data
    assert b'alert-warning' in response.data
    assert b'Item force deleted. Related records will show "Not Available".' in response.data

    # Check that the item is gone
    assert Item.query.get(item.id) is None

    # Check that bills and quotations still exist, but their items are now None/Not Available
    bill_page = client.get('/bills')
    assert b'Not Available' in bill_page.data or b'not available' in bill_page.data

    quotation_page = client.get('/quotations')
    assert b'Not Available' in quotation_page.data or b'not available' in quotation_page.data

    # Optionally, check inventory history, etc. 