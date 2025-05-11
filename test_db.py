from app import app, db, User, Item, Settings
from datetime import datetime
from sqlalchemy import text

def test_database():
    with app.app_context():
        try:
            # Test 1: Check if we can connect to the database
            print("Test 1: Checking database connection...")
            db.session.execute(text('SELECT 1'))
            print("✅ Database connection successful!")

            # Test 2: Check if we can read from the database
            print("\nTest 2: Checking if we can read data...")
            users = User.query.all()
            print(f"✅ Found {len(users)} users in the database")
            
            # Test 3: Check if we can write to the database
            print("\nTest 3: Checking if we can write data...")
            test_item = Item(
                name="Test Item",
                description="This is a test item",
                price=99.99,
                stock=10,
                hsn_sac_number="TEST123",
                tax_rate=18.0
            )
            db.session.add(test_item)
            db.session.commit()
            print("✅ Successfully wrote test item to database")
            
            # Clean up test data
            db.session.delete(test_item)
            db.session.commit()
            print("✅ Successfully cleaned up test data")

            print("\nAll database tests passed successfully! 🎉")
            
        except Exception as e:
            print(f"❌ Error during database test: {str(e)}")
            raise

if __name__ == '__main__':
    test_database() 