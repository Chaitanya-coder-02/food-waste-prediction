# Food Waste Prediction – Data Science Project

A Flask and MongoDB web application with Pandas, NumPy, Scikit-Learn, and Chart.js for hotel and canteen owners to track, analyze, and minimize daily food waste.

## Features

1. **Owner Registration & Login**:
   - Stores hotel/canteen owners in MongoDB collection `"owners"`.
   - Passwords hashed securely using Werkzeug scrypt.
   - Unique email index prevents duplicate registrations.
   - Strict owner data isolation: each owner only accesses their own food records.

2. **Operations Dashboard**:
   - Real-time today's food statistics (total items, quantity prepared, consumed, wasted, waste percentage).
   - Zero-division safety handling.
   - Interactive category-wise and daily trend charts.
   - Today's menu log table.

3. **Daily Food Entry**:
   - Food name, category, prepared quantity (kg), consumed quantity (kg), headcount, date.
   - Auto-derived day of the week.
   - Dynamic real-time calculation preview in UI.
   - Stored in MongoDB collection `"food_records"`.

4. **Food Records Master Log**:
   - Historical records table sorted by date (latest first).
   - Dynamic date and category filtering.
   - Delete meal records.

5. **Data Science Analysis**:
   - Powered by **Pandas** and **NumPy**.
   - 6 Interactive Chart.js charts:
     - Prepared vs Consumed vs Wasted (Bar Chart)
     - Consumed vs Wasted Split (Doughnut Chart)
     - Waste by Food Category (Bar Chart)
     - Daily Food Waste Trend (Line Chart)
     - Waste by Day of Week (Bar Chart)
     - People Served vs Food Waste (Scatter Plot with Pearson Correlation)
   - Descriptive KPIs: mean, median, standard deviation, max/min records.
   - Data-driven operational insights.

6. **Machine Learning Waste Prediction**:
   - Genuine **Scikit-Learn** `RandomForestRegressor` pipeline.
   - One-hot encoding of categories and days of week.
   - Evaluated with **MAE**, **RMSE**, and **R²** metrics.
   - Clearly distinguishes trained ML model from baseline formula estimates.

---

## How to Run on Windows (in VS Code)

### 1. Start MongoDB
Run the standalone database script:
```cmd
.\start_mongodb.bat
```
*(MongoDB runs on `localhost:27017` with permanent data storage in `mongodb/data`).*

### 2. Start the Flask Application
Run:
```cmd
python app.py
```
*(Or double-click `run_app.bat`)*

### 3. Open in Browser
Visit [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

### Run Automated Tests
```cmd
python test_workflow.py
```
