from app import app, db, User
from werkzeug.security import generate_password_hash
import os

def init_db():
    with app.app_context():
        try:
            print("Starting database initialization...")
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
                
        except Exception as e:
            print(f"Error during database initialization: {str(e)}")
            raise

if __name__ == '__main__':
    init_db() 