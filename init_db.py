from app import app, db, User
from werkzeug.security import generate_password_hash
import os

def init_db():
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            
            # Check if admin user exists
            admin = User.query.filter_by(username='admin').first()
            if not admin:
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
                # Reset admin password to ensure it's correct
                admin.set_password('admin123')
                db.session.commit()
                print("Admin user password reset successfully!")
        except Exception as e:
            print(f"Error during database initialization: {str(e)}")
            raise

if __name__ == '__main__':
    init_db() 