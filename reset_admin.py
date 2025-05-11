from app import app, db, User
import os

with app.app_context():
    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
    
    # Delete existing admin user if exists
    admin = User.query.filter_by(username=admin_username).first()
    if admin:
        db.session.delete(admin)
        db.session.commit()
    
    # Create new admin user
    admin = User(username=admin_username, role='admin')
    admin.set_password(admin_password)
    db.session.add(admin)
    db.session.commit()
    print("Admin user reset successfully!") 