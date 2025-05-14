from app import app, db
 
with app.app_context():
    with db.engine.connect() as conn:
        conn.execute(db.text('DROP TABLE IF EXISTS inventory_history'))
    db.create_all()
    print('inventory_history table reset successfully!') 