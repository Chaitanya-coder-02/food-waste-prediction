"""
Food Waste Prediction – Data Science Web Application
Flask + MongoDB + Pandas + NumPy + Scikit-Learn + Chart.js
"""

import os
import subprocess
import socket
from datetime import datetime
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, jsonify, abort
)
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId

from config import Config
import database
from ml_model import train_food_waste_model, predict_waste
from analysis_service import perform_data_science_analysis

def ensure_mongodb_running():
    """Ensure local MongoDB instance is running, starting mongod.exe if needed."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(0.5)
    is_open = sock.connect_ex(('127.0.0.1', 27017)) == 0
    sock.close()
    
    if not is_open:
        mongod_exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mongodb", "bin", "mongod.exe")
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mongodb", "data")
        if os.path.exists(mongod_exe):
            os.makedirs(db_path, exist_ok=True)
            try:
                subprocess.Popen(
                    [mongod_exe, "--dbpath", db_path, "--bind_ip", "127.0.0.1", "--port", "27017"],
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                )
                import time
                time.sleep(1.5)
            except Exception as e:
                print(f"Note: Could not launch local mongod: {e}")

# Start MongoDB before app initialization if needed
ensure_mongodb_running()

app = Flask(__name__)
app.config.from_object(Config)

# Initialize MongoDB connection and indexes
database.init_db(app)

# Login Required Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "owner_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

# Context Processor for Templates
@app.context_processor
def inject_globals():
    return {
        "current_owner": {
            "id": session.get("owner_id"),
            "name": session.get("owner_name", "Owner"),
            "hotel": session.get("hotel_name", "Hotel / Canteen"),
            "email": session.get("owner_email", "")
        } if "owner_id" in session else None,
        "today_str": datetime.now().strftime("%Y-%m-%d"),
        "now_year": datetime.now().year
    }

# ----------------- Authentication Routes -----------------

@app.route("/")
def home():
    if "owner_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if "owner_id" in session:
        return redirect(url_for("dashboard"))
        
    if request.method == "POST":
        owner_name = request.form.get("owner_name", "").strip()
        hotel_name = request.form.get("hotel_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        # Form Validation
        if not all([owner_name, hotel_name, email, password, confirm_password]):
            flash("All fields except phone number are required.", "danger")
            return render_template("register.html")
            
        if password != confirm_password:
            flash("Password and Confirm Password do not match.", "danger")
            return render_template("register.html")
            
        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html")
            
        # Check for existing email in MongoDB
        try:
            existing = database.find_owner_by_email(email)
            if existing:
                flash("An account with this email address already exists. Please log in.", "danger")
                return render_template("register.html")
                
            # Hash password and create owner in MongoDB
            password_hash = generate_password_hash(password)
            owner_id = database.create_owner({
                "owner_name": owner_name,
                "hotel_name": hotel_name,
                "email": email,
                "phone": phone,
                "password_hash": password_hash
            })
            
            flash("Registration successful! You can now log in with your credentials.", "success")
            return redirect(url_for("login"))
            
        except Exception as e:
            flash(f"Database error during registration: {str(e)}", "danger")
            return render_template("register.html")
            
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if "owner_id" in session:
        return redirect(url_for("dashboard"))
        
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        
        if not email or not password:
            flash("Please enter both email and password.", "danger")
            return render_template("login.html")
            
        try:
            owner = database.find_owner_by_email(email)
            if not owner or not check_password_hash(owner.get("password", ""), password):
                flash("Invalid email or password. Please try again.", "danger")
                return render_template("login.html")
                
            # Establish session securely
            session["owner_id"] = str(owner["_id"])
            session["owner_name"] = owner.get("owner_name", "Owner")
            session["hotel_name"] = owner.get("hotel_name", "Hotel / Canteen")
            session["owner_email"] = owner.get("email", email)
            
            flash(f"Welcome back, {session['owner_name']}!", "success")
            return redirect(url_for("dashboard"))
            
        except Exception as e:
            flash(f"Error connecting to database: {str(e)}", "danger")
            return render_template("login.html")
            
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login"))

# ----------------- Dashboard Route -----------------

@app.route("/dashboard")
@login_required
def dashboard():
    owner_id = session["owner_id"]
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # Retrieve owner's records from MongoDB
    all_records = database.get_owner_food_records(owner_id)
    today_records = [r for r in all_records if str(r.get("food_date")) == today_str]
    
    # Calculate today's food statistics from actual records
    today_items = len(today_records)
    today_prep = round(sum(float(r.get("quantity_prepared", 0.0)) for r in today_records), 2)
    today_cons = round(sum(float(r.get("quantity_consumed", 0.0)) for r in today_records), 2)
    today_waste = max(0.0, round(today_prep - today_cons, 2))
    
    # Safely compute today's waste percentage
    today_waste_pct = round((today_waste / today_prep) * 100, 2) if today_prep > 0 else 0.0
    
    # Crucial: Complete dictionary with all keys guaranteed to exist (fixes Jinja UndefinedError)
    today_stats = {
        "total_items": today_items,
        "quantity_prepared": today_prep,
        "quantity_consumed": today_cons,
        "quantity_wasted": today_waste,
        "waste_percentage": today_waste_pct
    }
    
    # Perform Data Science calculations for dashboard charts
    analysis = perform_data_science_analysis(all_records)
    
    return render_template(
        "dashboard.html",
        today_stats=today_stats,
        today_records=today_records,
        analysis=analysis,
        today_date=today_str,
        total_all_records=len(all_records)
    )

# ----------------- Food Entry Routes -----------------

@app.route("/add-food", methods=["GET", "POST"])
@login_required
def add_food():
    owner_id = session["owner_id"]
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    if request.method == "POST":
        food_name = request.form.get("food_name", "").strip()
        food_category = request.form.get("food_category", "").strip()
        prep_str = request.form.get("quantity_prepared", "").strip()
        cons_str = request.form.get("quantity_consumed", "").strip()
        people_str = request.form.get("people_served", "").strip()
        food_date = request.form.get("food_date", today_str).strip()
        
        # Validation
        if not food_name or not food_category or not prep_str or not cons_str or not food_date:
            flash("Please fill in all required fields.", "danger")
            return render_template("add_food.html", today_date=today_str)
            
        try:
            quantity_prepared = float(prep_str)
            quantity_consumed = float(cons_str)
            people_served = int(people_str) if people_str else 0
        except ValueError:
            flash("Prepared quantity, consumed quantity, and people served must be valid numbers.", "danger")
            return render_template("add_food.html", today_date=today_str)
            
        if quantity_prepared <= 0:
            flash("Prepared quantity must be greater than zero.", "danger")
            return render_template("add_food.html", today_date=today_str)
            
        if quantity_consumed < 0:
            flash("Consumed quantity cannot be negative.", "danger")
            return render_template("add_food.html", today_date=today_str)
            
        if quantity_consumed > quantity_prepared:
            flash("Consumed quantity cannot exceed the prepared quantity.", "danger")
            return render_template("add_food.html", today_date=today_str)
            
        # Automatically derive day of week from selected date
        try:
            date_obj = datetime.strptime(food_date, "%Y-%m-%d")
            day_of_week = date_obj.strftime("%A")
        except ValueError:
            day_of_week = datetime.now().strftime("%A")
            
        # Insert into MongoDB collection "food_records"
        try:
            database.insert_food_record({
                "owner_id": owner_id,
                "food_name": food_name,
                "food_category": food_category,
                "quantity_prepared": quantity_prepared,
                "quantity_consumed": quantity_consumed,
                "people_served": people_served,
                "food_date": food_date,
                "day_of_week": day_of_week
            })
            
            flash(f"Successfully recorded '{food_name}'! Wasted: {quantity_prepared - quantity_consumed:.2f} kg.", "success")
            return redirect(url_for("dashboard"))
            
        except Exception as e:
            flash(f"Error saving food record to MongoDB: {str(e)}", "danger")
            return render_template("add_food.html", today_date=today_str)
            
    return render_template("add_food.html", today_date=today_str)

# ----------------- Food Records Page -----------------

@app.route("/records")
@login_required
def records():
    owner_id = session["owner_id"]
    filter_date = request.args.get("date", "").strip() or None
    filter_category = request.args.get("category", "").strip() or None
    
    # Fetch filtered or all records for logged-in owner
    food_records = database.get_owner_food_records(
        owner_id,
        filter_date=filter_date,
        filter_category=filter_category
    )
    
    # Calculate summary metrics for the viewed records
    total_prep = round(sum(float(r.get("quantity_prepared", 0)) for r in food_records), 2)
    total_cons = round(sum(float(r.get("quantity_consumed", 0)) for r in food_records), 2)
    total_waste = round(sum(float(r.get("quantity_wasted", 0)) for r in food_records), 2)
    avg_waste_pct = round((total_waste / total_prep) * 100, 2) if total_prep > 0 else 0.0
    
    # Unique categories for filter dropdown
    all_owner_records = database.get_owner_food_records(owner_id)
    categories = sorted(list(set(r.get("food_category", "General") for r in all_owner_records)))
    
    return render_template(
        "records.html",
        records=food_records,
        categories=categories,
        filter_date=filter_date or "",
        filter_category=filter_category or "",
        summary={
            "count": len(food_records),
            "prepared": total_prep,
            "consumed": total_cons,
            "wasted": total_waste,
            "waste_pct": avg_waste_pct
        }
    )

@app.route("/records/delete/<record_id>", methods=["POST"])
@login_required
def delete_record(record_id):
    owner_id = session["owner_id"]
    db = database.get_db()
    if db is not None:
        try:
            # Secure delete: Ensure record belongs strictly to logged in owner
            res = db.food_records.delete_one({"_id": ObjectId(record_id), "owner_id": str(owner_id)})
            if res.deleted_count > 0:
                flash("Food record deleted successfully.", "success")
            else:
                flash("Record not found or unauthorized.", "danger")
        except Exception as e:
            flash(f"Error deleting record: {str(e)}", "danger")
    return redirect(url_for("records"))

# ----------------- Data Science Analysis Page -----------------

@app.route("/analysis")
@login_required
def analysis():
    owner_id = session["owner_id"]
    all_records = database.get_owner_food_records(owner_id)
    
    # Compute full Pandas & NumPy analysis
    results = perform_data_science_analysis(all_records)
    
    return render_template("analysis.html", analysis=results)

# ----------------- Food Waste Prediction Page -----------------

@app.route("/predict", methods=["GET", "POST"])
@login_required
def predict():
    owner_id = session["owner_id"]
    all_records = database.get_owner_food_records(owner_id)
    
    # Train Scikit-Learn Model dynamically on actual MongoDB records
    model_result = train_food_waste_model(all_records)
    
    prediction_result = None
    form_data = {
        "food_category": "Main Course",
        "day_of_week": datetime.now().strftime("%A"),
        "quantity_prepared": "",
        "people_served": ""
    }
    
    if request.method == "POST":
        category = request.form.get("food_category", "Main Course").strip()
        day = request.form.get("day_of_week", datetime.now().strftime("%A")).strip()
        prep_str = request.form.get("quantity_prepared", "").strip()
        people_str = request.form.get("people_served", "").strip()
        
        form_data = {
            "food_category": category,
            "day_of_week": day,
            "quantity_prepared": prep_str,
            "people_served": people_str
        }
        
        try:
            prep_val = float(prep_str)
            people_val = int(people_str) if people_str else 0
            
            if prep_val <= 0:
                flash("Prepared quantity must be greater than zero.", "danger")
            else:
                # Perform prediction
                prediction_result = predict_waste(model_result, {
                    "food_category": category,
                    "day_of_week": day,
                    "quantity_prepared": prep_val,
                    "people_served": people_val
                })
        except ValueError:
            flash("Please enter valid numerical values for prepared quantity and people served.", "danger")
            
    # Default category choices if none yet in DB
    existing_cats = model_result.get("categories") or [
        "Main Course", "Rice Dishes", "Curries & Gravy",
        "Breads", "Starters & Snacks", "Desserts", "Beverages"
    ]
    
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    return render_template(
        "predict.html",
        model_result=model_result,
        prediction=prediction_result,
        form_data=form_data,
        categories=existing_cats,
        days=days
    )

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
