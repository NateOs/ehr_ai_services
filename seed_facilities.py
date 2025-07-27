import uuid
from app.db import get_db_session
from sqlalchemy.orm import Session
from app.models.sql_models import Facility
from datetime import datetime

def seed_facilities():
    db: Session = next(get_db_session())
    
    try:
        # Check if facilities already exist
        existing_facilities = db.query(Facility).count()
        if existing_facilities > 0:
            print(f"Found {existing_facilities} existing facilities")
            facilities = db.query(Facility).all()
            for facility in facilities:
                print(f"Facility: {facility.name} (ID: {facility.id})")
            return
        
        # Create sample facilities
        facilities_data = [
            {"name": "General Hospital", "address": "123 Main St, Medical City, MC 12345"},
            {"name": "City Medical Center", "address": "456 Health Ave, Medical City, MC 12346"},
            {"name": "Regional Healthcare", "address": "789 Care Blvd, Medical City, MC 12347"},
        ]
        
        created_facilities = []
        for facility_data in facilities_data:
            facility = Facility(
                id=uuid.uuid4(),
                name=facility_data["name"],
                address=facility_data["address"],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            db.add(facility)
            created_facilities.append(facility)
        
        db.commit()
        
        print("Created facilities:")
        for facility in created_facilities:
            print(f"- {facility.name} (ID: {facility.id})")
            
    except Exception as e:
        db.rollback()
        print(f"Error seeding facilities: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_facilities()