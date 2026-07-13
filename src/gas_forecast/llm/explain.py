from __future__ import annotations

import os
import pandas as pd
import google.generativeai as genai

def _configure_gemini():
    """Retrieve API key and configure the google-generativeai SDK."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        try:
            from dotenv import load_dotenv
            load_dotenv("local.env")
            load_dotenv("notebooks/local.env")
            api_key = os.getenv("GEMINI_API_KEY")
        except ImportError:
            pass

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Please set GEMINI_API_KEY in your environment or notebooks/local.env."
        )
    genai.configure(api_key=api_key)

def generate_weekly_market_report(
    balance_df: pd.DataFrame,
    target_date: pd.Timestamp | str,
    region_name: str = "Lower 48",
    model_name: str = "gemini-3.5-flash",
) -> str:
    """
    Generate an LLM explainability report for a specific week's supply/demand balance and price movement.
    """
    _configure_gemini()
    
    target_dt = pd.to_datetime(target_date)
    
    # Sort and find the target week row and previous week row to compute changes
    df = balance_df.sort_values("date").reset_index(drop=True)
    target_idx_list = df[df["date"] == target_dt].index
    if len(target_idx_list) == 0:
        raise ValueError(f"Target date {target_date} not found in the balance sheet.")
    
    idx = target_idx_list[0]
    row = df.iloc[idx]
    
    prev_row = df.iloc[idx - 1] if idx > 0 else None
    
    # Compile metrics
    act_change = row["weekly_change_bcf"]
    storage = row["storage_bcf"]
    temp = row["temperature_f"]
    hdd = row["hdd"]
    cdd = row["cdd"]
    
    prod = row["dry_production"]
    res_com = row["res_com"]
    power = row["power_burn"]
    ind = row["industrial"]
    fuel = row["fuel_use"]
    bal = row["local_balance"]
    net_in = row["net_inflow_balancing"]
    price = row["price"]
    
    # Compute changes from previous week
    price_change_str = "N/A"
    storage_change_diff_str = "N/A"
    if prev_row is not None:
        price_diff = price - prev_row["price"]
        price_change_str = f"{price_diff:+.3f} $/MMBtu"
        
        storage_diff = act_change - prev_row["weekly_change_bcf"]
        storage_change_diff_str = f"{storage_diff:+.1f} Bcf"

    # Construct Prompt
    prompt = f"""
You are a senior energy market analyst writing a natural gas market weekly commentary.
Analyze the supply/demand balance, weather, and price dynamics for the week ending {target_dt.strftime('%B %d, %Y')} in the {region_name} region.

Here are the key metrics for the week:
- **Actual Storage Change**: {act_change:.1f} Bcf (Total Inventory: {storage:.1f} Bcf)
- **Change in storage change compared to last week**: {storage_change_diff_str}
- **Average Henry Hub Spot Price**: {price:.3f} $/MMBtu (Change from last week: {price_change_str})
- **Weather Conditions**:
  - Weekly Mean Temperature: {temp:.1f} °F
  - Heating Degree Days (HDD): {hdd:.1f} (indicates heating demand)
  - Cooling Degree Days (CDD): {cdd:.1f} (indicates power burn for air conditioning)
- **Weekly Supply & Demand Balance Sheet (Bcf)**:
  - Dry Production (Local): {prod:.1f} Bcf
  - Residential & Commercial Demand: {res_com:.1f} Bcf
  - Power Burn (Electricity): {power:.1f} Bcf
  - Industrial Demand: {ind:.1f} Bcf
  - Lease/Plant/Pipeline Fuel: {fuel:.1f} Bcf
  - Regional Local Balance (Production minus Consumption): {bal:.1f} Bcf (Positive = Local Surplus, Negative = Local Deficit)
  - Net Inflow & Trading Balancing Item: {net_in:.1f} Bcf (represents pipeline flows from other regions, imports/exports, and statistical discrepancies)

Instructions:
1. Write a professional, concise market analysis report (approx. 200-350 words).
2. Explain how the weather conditions (HDD/CDD) drove residential/commercial consumption and power burn this week.
3. Contrast the Local Balance (Production minus Consumption) and Net Inflow/Trading with the actual weekly storage change.
4. Provide a clear narrative on how this supply/demand balance tightness or looseness influenced the Henry Hub spot price change ({price_change_str}).
5. Format the report using clean Markdown with distinct headers:
   - **Market Overview**
   - **Weather and Demand Drivers**
   - **Supply and Storage Balance**
   - **Price Impact Analysis**

Do not add introductions like "Here is the report..." or formatting chatter. Just output the final Markdown report.
"""

    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    return response.text


def answer_market_question(
    balance_df: pd.DataFrame,
    target_date: pd.Timestamp | str,
    question: str,
    region_name: str = "Lower 48",
    model_name: str = "gemini-3.5-flash",
) -> str:
    """
    Answer a custom user question about the market data, disaggregation analysis, or modeling methodology.
    """
    _configure_gemini()
    
    target_ts = pd.to_datetime(target_date)
    df = balance_df.sort_values("date").reset_index(drop=True)
    target_idx_list = df[df["date"] == target_ts].index
    
    row_context = ""
    if len(target_idx_list) > 0:
        idx = target_idx_list[0]
        row = df.iloc[idx]
        row_context = f"""
For the selected week ending {target_ts.strftime('%B %d, %Y')} in the {region_name} region:
- Actual Storage Change: {row['weekly_change_bcf']:.1f} Bcf (Total Inventory: {row['storage_bcf']:.1f} Bcf)
- Henry Hub Price: {row['price']:.3f} $/MMBtu
- Dry Production: {row['dry_production']:.1f} Bcf
- Residential & Commercial Demand: {row['res_com']:.1f} Bcf
- Power Burn Demand: {row['power_burn']:.1f} Bcf
- Industrial Demand: {row['industrial']:.1f} Bcf
- Fuel Use: {row['fuel_use']:.1f} Bcf
- Local Balance (Prod - Cons): {row['local_balance']:.1f} Bcf
- Net Inflow & Trading: {row['net_inflow_balancing']:.1f} Bcf
"""

    prompt = f"""
You are a senior energy market researcher and quantitative developer of this Natural Gas Storage Forecasting & Supply-Demand Model.
The site performs structural modeling and disaggregation of EIA natural gas monthly state-level data into weekly balances using OLS temperature/price regressions, downscaling, and ratio-to-seasonal profile projections.

Context:
{row_context}

Overall Modeling Framework & Assumptions:
1. Balance Identity: Regional Net Balance = Dry Production - (ResCom + PowerBurn + Industrial + FuelUse).
2. Weather Regressions (OLS):
   - ResCom/Days = b0 + b1*(HDD/Days) + b2*(CDD/Days)
   - PowerBurn/Days = g0 + g1*(HDD/Days) + g2*(CDD/Days) + g3*Price
3. Regional Downscaling: Dry production and fuel use are allocated from national monthly reports using state Marketed Production shares and regional retail consumption ratios.
4. Forecasting: Multi-horizon forecasts (1-week, 4-week, End-of-Season) use a Recursive Forecaster that roll-forwards predictions by dynamically updating lag and rolling variables step-by-step.
5. Backtesting: Uses a date-based Expanding Window Splitter to test models on multiple folds historically with zero training data leaking into test sets.

User's Question:
"{question}"

Instructions:
Answer the user's question accurately, professionally, and concisely as the system creator/market analyst. Rely on the provided context and structural modeling specifications. If the question is about the data metrics or the modeling steps, reference the mathematical formulation or the specific data points shown above. Format your response in clean Markdown.
"""

    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    return response.text
