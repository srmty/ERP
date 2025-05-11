from app import app, db, User

with app.app_context():
    admin = User.query.filter_by(username='rabi').first()
    if not admin:
        admin = User(username='rabi', role='admin')
        admin.set_password('rabi123')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully!")
    else:
        print("Admin user already exists!") 