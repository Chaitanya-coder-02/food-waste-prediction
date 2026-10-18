"""
Data Science Analysis Service using Pandas and NumPy.
Performs comprehensive aggregations, trends, correlations, and insights
based strictly on actual MongoDB records for the logged-in owner.
"""

import pandas as pd
import numpy as np

def perform_data_science_analysis(records):
    """
    Analyzes owner food records using Pandas and NumPy.
    Returns structured results for rendering KPIs, charts, and data-driven insights.
    """
    if not records or len(records) == 0:
        return {
            "has_data": False,
            "message": "No food records found yet. Please add food details using the 'Add Food Details' form to unlock Data Science analyses and visualizations."
        }
    
    # Load into Pandas DataFrame
    df = pd.DataFrame(records)
    
    # Ensure numeric columns are strictly float/int
    df["quantity_prepared"] = pd.to_numeric(df["quantity_prepared"], errors="coerce").fillna(0.0)
    df["quantity_consumed"] = pd.to_numeric(df["quantity_consumed"], errors="coerce").fillna(0.0)
    
    # Recompute or verify wasted and waste_percentage
    if "quantity_wasted" not in df.columns:
        df["quantity_wasted"] = (df["quantity_prepared"] - df["quantity_consumed"]).clip(lower=0.0).round(2)
    else:
        df["quantity_wasted"] = pd.to_numeric(df["quantity_wasted"], errors="coerce").fillna(0.0)
        
    df["waste_percentage"] = np.where(
        df["quantity_prepared"] > 0,
        ((df["quantity_wasted"] / df["quantity_prepared"]) * 100).round(2),
        0.0
    )
    
    df["people_served"] = pd.to_numeric(df["people_served"], errors="coerce").fillna(0).astype(int)
    df["food_category"] = df["food_category"].fillna("General").astype(str)
    df["food_date"] = df["food_date"].astype(str)
    
    # 1. Overall Aggregations
    total_prepared = round(float(df["quantity_prepared"].sum()), 2)
    total_consumed = round(float(df["quantity_consumed"].sum()), 2)
    total_wasted = round(float(df["quantity_wasted"].sum()), 2)
    total_people = int(df["people_served"].sum())
    total_records = len(df)
    
    overall_waste_pct = round((total_wasted / total_prepared) * 100, 2) if total_prepared > 0 else 0.0

    # 2. Descriptive Statistics via Pandas & NumPy
    avg_waste_per_record = round(float(df["quantity_wasted"].mean()), 2)
    median_waste = round(float(df["quantity_wasted"].median()), 2)
    std_waste = round(float(df["quantity_wasted"].std(ddof=0)), 2)
    
    # 3. Maximum and Minimum Waste Records
    max_idx = df["quantity_wasted"].idxmax()
    min_idx = df["quantity_wasted"].idxmin()
    max_record = df.loc[max_idx].to_dict()
    min_record = df.loc[min_idx].to_dict()

    # 4. Category-wise Food Waste Analysis
    cat_grp = df.groupby("food_category").agg(
        total_prepared=("quantity_prepared", "sum"),
        total_consumed=("quantity_consumed", "sum"),
        total_wasted=("quantity_wasted", "sum"),
        record_count=("food_name", "count")
    ).reset_index()
    
    cat_grp["waste_pct"] = np.where(
        cat_grp["total_prepared"] > 0,
        ((cat_grp["total_wasted"] / cat_grp["total_prepared"]) * 100).round(2),
        0.0
    )
    cat_grp = cat_grp.sort_values(by="total_wasted", ascending=False)
    
    category_chart = {
        "labels": cat_grp["food_category"].tolist(),
        "wasted": [round(float(x), 2) for x in cat_grp["total_wasted"].tolist()],
        "prepared": [round(float(x), 2) for x in cat_grp["total_prepared"].tolist()],
        "consumed": [round(float(x), 2) for x in cat_grp["total_consumed"].tolist()],
        "percentages": [round(float(x), 2) for x in cat_grp["waste_pct"].tolist()]
    }

    # 5. Date-wise Food Waste Trend
    date_grp = df.groupby("food_date").agg(
        prepared=("quantity_prepared", "sum"),
        consumed=("quantity_consumed", "sum"),
        wasted=("quantity_wasted", "sum")
    ).sort_index().reset_index()
    
    date_chart = {
        "labels": date_grp["food_date"].tolist(),
        "prepared": [round(float(x), 2) for x in date_grp["prepared"].tolist()],
        "consumed": [round(float(x), 2) for x in date_grp["consumed"].tolist()],
        "wasted": [round(float(x), 2) for x in date_grp["wasted"].tolist()]
    }

    # 6. Day-of-the-Week Comparison
    weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_grp = df.groupby("day_of_week").agg(
        wasted=("quantity_wasted", "sum"),
        prepared=("quantity_prepared", "sum"),
        count=("food_name", "count")
    ).reindex(weekdays).fillna(0.0).reset_index()
    
    day_chart = {
        "labels": day_grp["day_of_week"].tolist(),
        "wasted": [round(float(x), 2) for x in day_grp["wasted"].tolist()],
        "prepared": [round(float(x), 2) for x in day_grp["prepared"].tolist()]
    }

    # 7. Scatter Data: People Served vs Food Waste & Correlation
    scatter_points = []
    for _, row in df.iterrows():
        scatter_points.append({
            "x": int(row["people_served"]),
            "y": round(float(row["quantity_wasted"]), 2),
            "food_name": str(row.get("food_name", "Item")),
            "date": str(row["food_date"])
        })
        
    correlation_coefficient = None
    if len(df) > 1 and df["people_served"].std() > 0 and df["quantity_wasted"].std() > 0:
        corr_matrix = np.corrcoef(df["people_served"], df["quantity_wasted"])
        correlation_coefficient = round(float(corr_matrix[0, 1]), 3)

    # 8. Data-Driven Insights
    insights = []
    
    # Insight 1: Highest Waste Category
    if not cat_grp.empty:
        top_cat = cat_grp.iloc[0]
        insights.append({
            "title": "Highest Waste Category",
            "badge": "Category Impact",
            "type": "warning" if top_cat["total_wasted"] > 0 else "info",
            "text": f"'{top_cat['food_category']}' accounts for the highest food waste with {top_cat['total_wasted']:.2f} kg wasted ({top_cat['waste_pct']:.1f}% waste rate)."
        })
        
    # Insight 2: Peak Waste Day
    active_days = day_grp[day_grp["wasted"] > 0]
    if not active_days.empty:
        peak_day = active_days.sort_values(by="wasted", ascending=False).iloc[0]
        insights.append({
            "title": "Peak Waste Day",
            "badge": "Weekly Pattern",
            "type": "info",
            "text": f"{peak_day['day_of_week']} recorded the maximum cumulative food waste ({peak_day['wasted']:.2f} kg across recorded services)."
        })
        
    # Insight 3: Waste per Person Served
    if total_people > 0:
        waste_per_person = round((total_wasted / total_people), 3)
        insights.append({
            "title": "Average Waste Per Guest",
            "badge": "Efficiency Metric",
            "type": "success" if waste_per_person < 0.1 else "warning",
            "text": f"On average, each guest served accounts for approximately {waste_per_person * 1000:.0f} grams ({waste_per_person:.3f} kg) of unconsumed food."
        })
        
    # Insight 4: Correlation interpretation
    if correlation_coefficient is not None:
        if correlation_coefficient > 0.5:
            corr_text = f"Strong positive correlation ({correlation_coefficient}) observed: larger banquet sizes significantly increase surplus waste."
        elif correlation_coefficient > 0.1:
            corr_text = f"Moderate positive correlation ({correlation_coefficient}) between people served and food waste."
        elif correlation_coefficient < -0.1:
            corr_text = f"Slight negative correlation ({correlation_coefficient}): larger crowds are managed with better portion economy."
        else:
            corr_text = f"Near-zero correlation ({correlation_coefficient}): food waste is driven more by item type/recipe forecasting than crowd headcount."
        insights.append({
            "title": "Headcount vs Waste Correlation",
            "badge": "Statistical Correlation",
            "type": "info",
            "text": corr_text
        })

    return {
        "has_data": True,
        "total_records": total_records,
        "total_prepared": total_prepared,
        "total_consumed": total_consumed,
        "total_wasted": total_wasted,
        "total_people": total_people,
        "overall_waste_pct": overall_waste_pct,
        "avg_waste_per_record": avg_waste_per_record,
        "median_waste": median_waste,
        "std_waste": std_waste,
        "max_record": max_record,
        "min_record": min_record,
        "category_chart": category_chart,
        "date_chart": date_chart,
        "day_chart": day_chart,
        "scatter_points": scatter_points,
        "correlation_coefficient": correlation_coefficient,
        "insights": insights
    }
