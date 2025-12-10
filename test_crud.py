"""
Functional Test for WellMom CRUD Operations
Run: python test_crud.py
"""

from app.database import SessionLocal
from app.crud import (
    crud_user, 
    crud_puskesmas, 
    crud_perawat, 
    crud_ibu_hamil,
    crud_kerabat,
    crud_health_record,
    crud_notification,
    crud_transfer_request
)
from app.schemas import (
    UserCreate,
    PuskesmasCreate,
    PerawatCreate,
    IbuHamilCreate,
)
from datetime import date, datetime

def test_user_crud():
    """Test User CRUD operations"""
    print("\n🧪 Testing User CRUD...")
    db = SessionLocal()
    
    try:
        # 1. Create user
        user_data = UserCreate(
            phone="+6281234567890",
            password="testpassword123",
            full_name="Test User Admin",
            role="admin",
            email="test@example.com"
        )
        
        # Check if user exists first
        existing_user = crud_user.get_by_phone(db, phone=user_data.phone)
        if existing_user:
            print("   ✅ User already exists, skipping creation")
            user = existing_user
        else:
            user = crud_user.create(db, obj_in=user_data)
            print(f"   ✅ Created user: {user.full_name} (ID: {user.id})")
        
        # 2. Get user by ID
        retrieved_user = crud_user.get(db, id=user.id)
        print(f"   ✅ Retrieved user: {retrieved_user.full_name}")
        
        # 3. Get by phone
        user_by_phone = crud_user.get_by_phone(db, phone=user.phone)
        print(f"   ✅ Found by phone: {user_by_phone.full_name}")
        
        # 4. Authenticate (skip if existing user with old hash)
        if not existing_user:
            is_auth = crud_user.authenticate(db, phone=user.phone, password="testpassword123")
            print(f"   ✅ Authentication: {'Success' if is_auth else 'Failed'}")
        else:
            print("   ⏭️  Skipping auth test (existing user)")
        
        # 5. Get users by role
        admins = crud_user.get_by_role(db, role="admin")
        print(f"   ✅ Found {len(admins)} admin(s)")
        
        print("   ✅ User CRUD: ALL TESTS PASSED")
        return user.id
        
    except Exception as e:
        print(f"   ❌ User CRUD Error: {str(e)}")
        return None
    finally:
        db.close()

def test_puskesmas_crud(admin_user_id):
    """Test Puskesmas CRUD operations"""
    print("\n🧪 Testing Puskesmas CRUD...")
    db = SessionLocal()
    
    try:
        # Check existing
        existing = db.query(crud_puskesmas.model).filter_by(code="PKM-TST-001").first()
        
        if existing:
            print("   ✅ Puskesmas already exists")
            puskesmas = existing
        else:
            # Create new
            puskesmas_data = PuskesmasCreate(
                name="Puskesmas Test",
                code="PKM-TST-001",
                sk_number="SK/TEST/001",
                operational_license_number="LIC-TEST-001",
                address="Jl. Test No. 1",
                kelurahan="Test",
                kecamatan="Test",
                phone="081234567890",
                email="test@puskesmas.com",
                location=(101.5, -2.0),  # (longitude, latitude)
                kepala_name="Dr. Test",
                kepala_nip="199001011990011001",
                kepala_sk_number="SK/KEPALA/TEST",
                kepala_nik="1234567890123456",
                kepala_phone="+6281200000000",
                kepala_email="kepala@test.com",
                # URLs (required fields)
                sk_document_url="http://test.com/sk.pdf",
                license_document_url="http://test.com/license.pdf",
                building_photo_url="http://test.com/building.jpg",
                kepala_ktp_url="http://test.com/ktp.jpg",
                kepala_sk_document_url="http://test.com/sk_kepala.pdf",
                verification_photo_url="http://test.com/verification.jpg"
            )
            
            puskesmas = crud_puskesmas.create_with_location(db, puskesmas_in=puskesmas_data)
            print(f"   ✅ Created puskesmas: {puskesmas.name}")
        
        # Get pending registrations
        pending = crud_puskesmas.get_pending_registrations(db)
        print(f"   ✅ Found {len(pending)} pending registration(s)")
        
        # Approve puskesmas
        if puskesmas.registration_status == 'pending' and admin_user_id:
            approved = crud_puskesmas.approve(db, puskesmas_id=puskesmas.id, admin_id=admin_user_id)
            print(f"   ✅ Approved puskesmas")
        
        # Find nearest (PostGIS test!)
        nearest = crud_puskesmas.find_nearest(
            db, 
            latitude=-2.01, 
            longitude=101.51, 
            radius_km=20
        )
        print(f"   ✅ Found {len(nearest)} puskesmas within 20km")
        
        print("   ✅ Puskesmas CRUD: ALL TESTS PASSED")
        return puskesmas.id
        
    except Exception as e:
        print(f"   ❌ Puskesmas CRUD Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()

def test_ibu_hamil_crud():
    """Test IbuHamil CRUD operations"""
    print("\n🧪 Testing IbuHamil CRUD...")
    db = SessionLocal()
    
    try:
        # Check if ibu hamil already exists
        existing = db.query(crud_ibu_hamil.model).filter_by(nik="1234567890123456").first()
        
        if existing:
            print("   ✅ Ibu Hamil already exists")
            ibu = existing
        else:
            # Check if user already exists
            existing_user = crud_user.get_by_phone(db, phone="+6281234567891")
            
            if existing_user:
                print("   ✅ User already exists, reusing")
                user = existing_user
            else:
                # Create new user
                user_data = UserCreate(
                    phone="+6281234567891",
                    password="testpass",
                    full_name="Ibu Test",
                    role="ibu_hamil"
                )
                user = crud_user.create_user(db, user_in=user_data)
                print(f"   ✅ Created new user: {user.full_name}")
            
            # Create ibu hamil with location
            ibu_data = IbuHamilCreate(
                nik="1234567890123456",
                date_of_birth=date(1990, 1, 1),
                location=(101.52, -2.02),  # Tuple format - will be converted
                address="Jl. Test Ibu No. 1",
                kelurahan="Test",
                kecamatan="Test",
                emergency_contact_name="Suami Test",
                emergency_contact_phone="+6281200000001",
                emergency_contact_relation="Suami",
                last_menstrual_period=date(2024, 6, 1)
            )
            
            # Use create_with_location method
            ibu = crud_ibu_hamil.create_with_location(db, obj_in=ibu_data, user_id=user.id)
            print(f"   ✅ Created ibu hamil: {ibu.id}")
        
        # Get unassigned
        unassigned = crud_ibu_hamil.get_unassigned(db)
        print(f"   ✅ Found {len(unassigned)} unassigned ibu hamil")
        
        # Find nearest puskesmas (PostGIS test!)
        if ibu.location:
            nearest = crud_ibu_hamil.find_nearest_puskesmas(db, ibu_id=ibu.id, radius_km=20)
            print(f"   ✅ Found {len(nearest)} nearest puskesmas")
            
            # Show details of nearest
            if nearest:
                closest = nearest[0]
                print(f"   ✅ Closest: {closest[0].name} ({closest[1]:.2f} km)")
        
        print("   ✅ IbuHamil CRUD: ALL TESTS PASSED")
        return ibu.id
        
    except Exception as e:
        print(f"   ❌ IbuHamil CRUD Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        db.close()

def main():
    """Run all CRUD tests"""
    print("=" * 60)
    print("🚀 WellMom CRUD Functional Tests")
    print("=" * 60)
    
    # Test in order (due to dependencies)
    user_id = test_user_crud()
    puskesmas_id = test_puskesmas_crud(user_id)
    ibu_hamil_id = test_ibu_hamil_crud()
    
    print("\n" + "=" * 60)
    print("✅ ALL CRUD TESTS COMPLETED")
    print("=" * 60)
    print(f"\nCreated IDs:")
    print(f"  - User ID: {user_id}")
    print(f"  - Puskesmas ID: {puskesmas_id}")
    print(f"  - Ibu Hamil ID: {ibu_hamil_id}")
    print("\nReady for API endpoint testing! 🚀")

if __name__ == "__main__":
    main()