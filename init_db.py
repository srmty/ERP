from app import app, db, User
from werkzeug.security import generate_password_hash
import os
import time

def init_db():
    max_retries = 3
    retry_delay = 5  # seconds
    
    for attempt in range(max_retries):
        try:
            with app.app_context():
                print(f"Database initialization attempt {attempt + 1}/{max_retries}")
                print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
                
                # Create all tables
                print("Creating database tables...")
                db.create_all()
                
                # Check if admin user exists
                print("Checking for admin user...")
                admin = User.query.filter_by(username='admin').first()
                if not admin:
                    print("Admin user not found, creating new admin...")
                    # Create admin user
                    admin = User(
                        username='admin',
                        role='admin'
                    )
                    admin.set_password('admin123')  # Change this password after first login
                    db.session.add(admin)
                    db.session.commit()
                    print("Admin user created successfully!")
                else:
                    print("Admin user found, resetting password...")
                    # Reset admin password to ensure it's correct
                    admin.set_password('admin123')
                    db.session.commit()
                    print("Admin user password reset successfully!")
                
                # Verify admin user
                admin = User.query.filter_by(username='admin').first()
                print(f"Admin user verification: {admin is not None}")
                if admin:
                    print(f"Admin role: {admin.role}")
                    print(f"Admin password hash: {admin.password_hash}")
                
                return True  # Success
                
        except Exception as e:
            print(f"Error during database initialization (attempt {attempt + 1}): {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Failed to initialize database.")
                raise

if __name__ == '__main__':
    init_db() 