import pytest
from app import app, db

@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_client() as client:
        yield client

def test_index(client):
    resp = client.get('/')
    assert resp.status_code in (200, 302)

def test_add_item_get(client):
    resp = client.get('/add_item')
    assert resp.status_code in (200, 302)

def test_create_bill_get(client):
    resp = client.get('/create_bill')
    assert resp.status_code in (200, 302)

def test_bills(client):
    resp = client.get('/bills')
    assert resp.status_code in (200, 302)

def test_settings(client):
    resp = client.get('/settings')
    assert resp.status_code in (200, 302)

def test_customers(client):
    resp = client.get('/customers')
    assert resp.status_code in (200, 302)

def test_add_customer_get(client):
    resp = client.get('/add_customer')
    assert resp.status_code in (200, 302)

def test_inventory_history(client):
    resp = client.get('/inventory_history')
    assert resp.status_code in (200, 302)

def test_quotations_get(client):
    resp = client.get('/quotations')
    assert resp.status_code in (200, 302)

def test_export_bills(client):
    resp = client.get('/export/bills')
    assert resp.status_code in (200, 302)

def test_export_customers(client):
    resp = client.get('/export/customers')
    assert resp.status_code in (200, 302)

def test_export_inventory(client):
    resp = client.get('/export/inventory')
    assert resp.status_code in (200, 302)

def test_login_get(client):
    resp = client.get('/login')
    assert resp.status_code in (200, 302)

def test_logout(client):
    resp = client.get('/logout')
    assert resp.status_code in (200, 302)

def test_reset_db(client):
    resp = client.get('/reset_db')
    assert resp.status_code in (200, 302) 