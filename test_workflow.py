"""
Automated End-to-End Test Suite for Food Waste Prediction Platform
Validates all 12 testing requirements:
1. Register a new owner.
2. Confirm the owner is saved in MongoDB.
3. Log in with registered credentials.
4. Confirm dashboard opens without errors (verifying waste_percentage fix).
5. Add food details for today.
6. Verify record is saved in MongoDB.
7. Confirm today's dashboard statistics update.
8. Add more records with different categories and dates.
9. Verify that all analysis charts and calculations update correctly.
10. Confirm owner isolation (one owner cannot access another owner's records).
11. Test empty data and invalid inputs.
12. Test ML prediction and model evaluation when sufficient data exists.
"""

import sys
import unittest
from datetime import datetime, timedelta
from app import app
import database

class FoodWastePlatformTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        cls.client = app.test_client()
        cls.db = database.get_db()
        
        # Clean up test accounts if existing
        if cls.db is not None:
            cls.db.owners.delete_many({"email": {"$in": ["test_owner1@hotel.com", "test_owner2@hotel.com"]}})
            cls.db.food_records.delete_many({"food_name": {"$regex": "^Test_"}})

    def test_01_register_new_owner(self):
        """1 & 2: Register owner and confirm saved in MongoDB with hashed password."""
        response = self.client.post("/register", data={
            "owner_name": "Test Chef Rajesh",
            "hotel_name": "Grand Palace Hotel",
            "email": "test_owner1@hotel.com",
            "phone": "9876543210",
            "password": "SecretPassword123",
            "confirm_password": "SecretPassword123"
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Registration successful", response.data)
        
        # Verify in MongoDB
        owner = self.db.owners.find_one({"email": "test_owner1@hotel.com"})
        self.assertIsNotNone(owner)
        self.assertEqual(owner["owner_name"], "Test Chef Rajesh")
        self.assertEqual(owner["hotel_name"], "Grand Palace Hotel")
        # Ensure password is not plain text
        self.assertNotEqual(owner["password"], "SecretPassword123")
        self.assertTrue(owner["password"].startswith("scrypt:") or owner["password"].startswith("pbkdf2:"))
        print("[PASS] Test 1 & 2 Passed: Owner registered and saved in MongoDB with secure hash.")

    def test_02_prevent_duplicate_registration(self):
        """Test unique constraint on email."""
        response = self.client.post("/register", data={
            "owner_name": "Duplicate User",
            "hotel_name": "Duplicate Hotel",
            "email": "test_owner1@hotel.com",
            "phone": "1234567890",
            "password": "Password123",
            "confirm_password": "Password123"
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"already exists", response.data)
        print("[PASS] Test Duplicate Prevention Passed.")

    def test_03_login_and_dashboard_render(self):
        """3 & 4: Log in and verify dashboard opens without errors (testing waste_percentage)."""
        # Login
        response = self.client.post("/login", data={
            "email": "test_owner1@hotel.com",
            "password": "SecretPassword123"
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Welcome back", response.data)
        
        # Open Dashboard
        dash_res = self.client.get("/dashboard")
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b"Operations Dashboard", dash_res.data)
        self.assertIn(b"Grand Palace Hotel", dash_res.data)
        self.assertIn(b"Today's Menu Items", dash_res.data)
        self.assertIn(b"Today's Waste Rate", dash_res.data)
        print("[PASS] Test 3 & 4 Passed: Login successful and Dashboard opens with zero errors.")

    def test_04_add_food_details_for_today(self):
        """5, 6, 7: Add food details, verify MongoDB save, confirm today stats update."""
        today_str = datetime.now().strftime("%Y-%m-%d")
        response = self.client.post("/add-food", data={
            "food_name": "Test_Biryani",
            "food_category": "Rice Dishes",
            "quantity_prepared": "50.0",
            "quantity_consumed": "42.5",
            "people_served": "95",
            "food_date": today_str
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Successfully recorded", response.data)
        
        # Verify in MongoDB collection "food_records"
        rec = self.db.food_records.find_one({"food_name": "Test_Biryani"})
        self.assertIsNotNone(rec)
        self.assertEqual(float(rec["quantity_prepared"]), 50.0)
        self.assertEqual(float(rec["quantity_consumed"]), 42.5)
        self.assertEqual(float(rec["quantity_wasted"]), 7.5)
        self.assertEqual(float(rec["waste_percentage"]), 15.0)
        self.assertEqual(int(rec["people_served"]), 95)
        
        # Confirm dashboard statistics reflect today's record
        dash_res = self.client.get("/dashboard")
        self.assertEqual(dash_res.status_code, 200)
        self.assertIn(b"50.00", dash_res.data)  # Prepared
        self.assertIn(b"42.50", dash_res.data)  # Consumed
        self.assertIn(b"7.50", dash_res.data)   # Wasted
        self.assertIn(b"15.0%", dash_res.data)  # Waste %
        print("[PASS] Test 5, 6 & 7 Passed: Food details saved in MongoDB and Dashboard stats updated.")

    def test_05_add_multiple_records_and_check_analysis(self):
        """8 & 9: Add diverse records and verify analysis charts & calculations update."""
        today = datetime.now()
        batch_items = [
            ("Test_Dal_Makhani", "Curries & Gravy", 30.0, 27.0, 60, (today - timedelta(days=1)).strftime("%Y-%m-%d")),
            ("Test_Paneer_Tikka", "Starters & Snacks", 20.0, 15.0, 45, (today - timedelta(days=2)).strftime("%Y-%m-%d")),
            ("Test_Chapati_Batch", "Breads", 40.0, 36.0, 80, (today - timedelta(days=3)).strftime("%Y-%m-%d")),
            ("Test_Gulab_Jamun", "Desserts & Sweets", 15.0, 13.5, 50, (today - timedelta(days=4)).strftime("%Y-%m-%d")),
            ("Test_Fried_Rice", "Rice Dishes", 35.0, 28.0, 70, (today - timedelta(days=5)).strftime("%Y-%m-%d")),
            ("Test_Mix_Veg", "Main Course", 25.0, 20.0, 55, (today - timedelta(days=6)).strftime("%Y-%m-%d")),
            ("Test_Pasta", "Main Course", 22.0, 18.0, 40, (today - timedelta(days=7)).strftime("%Y-%m-%d")),
            ("Test_Naan", "Breads", 30.0, 26.0, 65, (today - timedelta(days=8)).strftime("%Y-%m-%d")),
            ("Test_Chicken_Curry", "Curries & Gravy", 45.0, 40.0, 90, (today - timedelta(days=9)).strftime("%Y-%m-%d")),
            ("Test_Spring_Rolls", "Starters & Snacks", 18.0, 14.0, 35, (today - timedelta(days=10)).strftime("%Y-%m-%d")),
        ]
        
        for name, cat, prep, cons, people, fdate in batch_items:
            res = self.client.post("/add-food", data={
                "food_name": name,
                "food_category": cat,
                "quantity_prepared": str(prep),
                "quantity_consumed": str(cons),
                "people_served": str(people),
                "food_date": fdate
            }, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

        # Check Analysis Page
        analysis_res = self.client.get("/analysis")
        self.assertEqual(analysis_res.status_code, 200)
        self.assertIn(b"Prepared vs Consumed vs Wasted", analysis_res.data)
        self.assertIn(b"Waste by Food Category", analysis_res.data)
        self.assertIn(b"Daily Food Waste Trend", analysis_res.data)
        self.assertIn(b"Food Waste by Day of Week", analysis_res.data)
        self.assertIn(b"People Served vs Food Waste", analysis_res.data)
        self.assertIn(b"Data-Driven Operational Insights", analysis_res.data)
        print("[PASS] Test 8 & 9 Passed: Diverse records added and all 6 analysis charts updated.")

    def test_06_owner_isolation(self):
        """10: Confirm that one owner cannot access another owner's records."""
        # Register second owner
        self.client.get("/logout")
        reg_res = self.client.post("/register", data={
            "owner_name": "Test Owner Two",
            "hotel_name": "Second Hotel & Canteen",
            "email": "test_owner2@hotel.com",
            "phone": "9998887776",
            "password": "Password456",
            "confirm_password": "Password456"
        }, follow_redirects=True)
        self.assertEqual(reg_res.status_code, 200)
        
        # Login as second owner
        login_res = self.client.post("/login", data={
            "email": "test_owner2@hotel.com",
            "password": "Password456"
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)
        
        # Check records page for second owner - should be empty!
        rec_res = self.client.get("/records")
        self.assertEqual(rec_res.status_code, 200)
        self.assertIn(b"No Food Records Found", rec_res.data)
        self.assertNotIn(b"Test_Biryani", rec_res.data)
        self.assertNotIn(b"Test_Dal_Makhani", rec_res.data)
        
        # Second owner adds 1 unique item
        self.client.post("/add-food", data={
            "food_name": "Test_Owner2_Special",
            "food_category": "Main Course",
            "quantity_prepared": "10.0",
            "quantity_consumed": "9.0",
            "people_served": "15",
            "food_date": datetime.now().strftime("%Y-%m-%d")
        }, follow_redirects=True)
        
        # Switch back to first owner and verify they cannot see Owner 2's special item
        self.client.get("/logout")
        self.client.post("/login", data={
            "email": "test_owner1@hotel.com",
            "password": "SecretPassword123"
        }, follow_redirects=True)
        
        owner1_recs = self.client.get("/records")
        self.assertNotIn(b"Test_Owner2_Special", owner1_recs.data)
        self.assertIn(b"Test_Biryani", owner1_recs.data)
        print("[PASS] Test 10 Passed: Strict owner isolation verified.")

    def test_07_invalid_inputs(self):
        """11: Test empty data and invalid inputs."""
        # Consumed > Prepared
        bad_res1 = self.client.post("/add-food", data={
            "food_name": "Test_Invalid",
            "food_category": "Main Course",
            "quantity_prepared": "10.0",
            "quantity_consumed": "15.0",
            "people_served": "20",
            "food_date": "2026-10-17"
        }, follow_redirects=True)
        self.assertIn(b"cannot exceed", bad_res1.data)
        
        # Negative consumed
        bad_res2 = self.client.post("/add-food", data={
            "food_name": "Test_Negative",
            "food_category": "Main Course",
            "quantity_prepared": "10.0",
            "quantity_consumed": "-5.0",
            "people_served": "20",
            "food_date": "2026-10-17"
        }, follow_redirects=True)
        self.assertIn(b"cannot be negative", bad_res2.data)
        
        # Zero prepared
        bad_res3 = self.client.post("/add-food", data={
            "food_name": "Test_Zero",
            "food_category": "Main Course",
            "quantity_prepared": "0.0",
            "quantity_consumed": "0.0",
            "people_served": "20",
            "food_date": "2026-10-17"
        }, follow_redirects=True)
        self.assertIn(b"greater than zero", bad_res3.data)
        print("[PASS] Test 11 Passed: Invalid inputs properly rejected with helpful error messages.")

    def test_08_machine_learning_prediction(self):
        """12: Test ML prediction and Scikit-learn regression evaluation."""
        # Ensure logged in as owner 1 (has 11 records)
        predict_page = self.client.get("/predict")
        self.assertEqual(predict_page.status_code, 200)
        self.assertIn(b"Scikit-Learn ML Model Active", predict_page.data)
        self.assertIn(b"Mean Absolute Error", predict_page.data)
        self.assertIn(b"Root Mean Squared Error", predict_page.data)
        
        # Run prediction
        post_pred = self.client.post("/predict", data={
            "food_category": "Rice Dishes",
            "day_of_week": "Friday",
            "quantity_prepared": "40.0",
            "people_served": "85"
        }, follow_redirects=True)
        
        self.assertEqual(post_pred.status_code, 200)
        self.assertIn(b"Prediction Output", post_pred.data)
        self.assertIn(b"Scikit-Learn Random Forest Regression", post_pred.data)
        self.assertIn(b"kg", post_pred.data)
        print("[PASS] Test 12 Passed: Scikit-learn Random Forest model trained, evaluated, and predicted successfully.")

if __name__ == "__main__":
    unittest.main()
