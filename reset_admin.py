from app import app, db, User

with app.app_context():
    # Delete existing admin user if exists
    admin = User.query.filter_by(username='rabi').first()
    if admin:
        db.session.delete(admin)
        db.session.commit()
    
    # Create new admin user
    admin = User(username='rabi', role='admin')
    admin.set_password('rabi123')
    db.session.add(admin)
    db.session.commit()
    print("Admin user reset successfully!") 