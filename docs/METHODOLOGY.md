This document details the complete mathematical formulation, regional downscaling procedures, and structural modeling assumptions underlying the Gas Market Platform.

---

### 1. Monthly Weather Regressions (OLS)
For the weather-sensitive components of regional demand, namely **Residential & Commercial (ResCom)** and **Power Burn**, we fit ordinary least squares (OLS) regression models on monthly data. To eliminate the confounding effect of varying calendar month lengths, all variables are normalized to daily rates before estimation.

#### A. Residential & Commercial (ResCom) Demand
The ResCom model explains space heating and cooling requirements based on Heating Degree Days (HDD) and Cooling Degree Days (CDD):

$$
\frac{\text{ResCom}_{r, M}}{D_M} = \beta_0 + \beta_1 \left(\frac{\text{HDD}_{r, M}}{D_M}\right) + \beta_2 \left(\frac{\text{CDD}_{r, M}}{D_M}\right) + \epsilon_{r, M}
$$

where:
*   $r$ is the region and $M$ is the monthly period.
*   $D_M$ is the number of days in month $M$.
*   $\text{ResCom}_{r, M}$ is the total regional residential and commercial gas demand (Bcf) in month $M$.
*   $\text{HDD}_{r, M}$ and $\text{CDD}_{r, M}$ are the total heating and cooling degree days for region $r$ in month $M$.
*   $\beta_0$ represents the base load demand (non-weather-sensitive pilot lights, cooking, etc.).
*   $\beta_1$ represents the space heating sensitivity (HDD slope).
*   $\beta_2$ represents the cooling/seasonal sensitivity (CDD slope).

#### B. Power Burn Demand
The Power Burn model explains gas consumption in the electricity sector. It incorporates weather variables (winter heating peaks and summer cooling peaks) and the regional Citygate price index to capture price-driven coal-to-gas or gas-to-coal generation switching:

$$
\frac{\text{Power Burn}_{r, M}}{D_M} = \gamma_0 + \gamma_1 \left(\frac{\text{HDD}_{r, M}}{D_M}\right) + \gamma_2 \left(\frac{\text{CDD}_{r, M}}{D_M}\right) + \gamma_3 P_{r, M} + \eta_{r, M}
$$

where:
*   $P_{r, M}$ is the monthly regional Citygate price index (\$/Mcf, same scale as \$/MMBtu), as defined in Section 4.
*   $\gamma_3$ represents the price elasticity of power burn (typically negative, capturing fuel substitution or demand destruction under high prices).

#### C. Weekly Estimation and Physical Constraints
To estimate weekly demand rates, we input daily-normalized weekly weather variables (weekly HDD and CDD divided by 7) and weekly regional spot prices into the fitted models, scale the daily rates to the 7-day weekly period, and apply a non-negativity constraint via clipping:

$$
\text{ResCom}_{r, t} = \max\left(0, \ 7 \times \left( \hat{\beta}_0 + \hat{\beta}_1 \frac{\text{HDD}_{r, t}}{7} + \hat{\beta}_2 \frac{\text{CDD}_{r, t}}{7} \right)\right)
$$

$$
\text{Power Burn}_{r, t} = \max\left(0, \ 7 \times \left( \hat{\gamma}_0 + \hat{\gamma}_1 \frac{\text{HDD}_{r, t}}{7} + \hat{\gamma}_2 \frac{\text{CDD}_{r, t}}{7} + \hat{\gamma}_3 P_{r, t} \right)\right)
$$

where $P_{r, t}$ is the projected weekly regional Citygate price index (\$/Mcf), as defined in Section 4.

---

### 2. Regional Dry Production Allocation
While the EIA publishes weekly national storage changes, detailed state and regional dry natural gas production data are only available on a lagged, monthly basis. To construct a timely weekly regional balance sheet, we downscale monthly national Dry Gas Production ($\text{US Dry Prod}_M$, EIA Series `N9070US2`) to the storage region $r$ using the regional share of monthly state Marketed Production ($M_{s, M}$, EIA Series prefix `N9050`):

$$
\text{Dry Production}_{r, M} = \text{US Dry Prod}_M \times \theta_{r, M}^{\text{prod}}
$$

where the production allocation ratio $\theta_{r, M}^{\text{prod}}$ is defined as:

$$
\theta_{r, M}^{\text{prod}} = \frac{\sum_{s \in r} M_{s, M}}{\sum_{s \in \text{US}} M_{s, M}}
$$

where:
*   $M_{s, M}$ is the marketed production of state $s$ in month $M$.
*   $s \in r$ indicates the set of states belonging to storage region $r$ (according to the official EIA Weekly Natural Gas Storage Report geography).
*   $\sum_{s \in \text{US}} M_{s, M}$ is the total marketed production across all 50 states (proxied by EIA Series `N9050US2`).

#### Reporting Lag & Constant-Share Forward-Fill Assumption
EIA state-level marketed production (`N9050ST2`) carries a significantly longer reporting lag (~12–18 months) than the national dry production series (`N9070US2`), which is updated within ~4 weeks. Additionally, some low-production states (e.g. Iowa, Minnesota, Wisconsin in the Midwest) have no separate state-level marketed production series published by the EIA at all.

To prevent the production allocation ratio from collapsing to zero during the lag window — which would artificially zero out regional dry production — we apply a **constant-share forward-fill**: the last known ratio $\theta_{r, M^*}^{\text{prod}}$ (where $M^*$ is the most recent month with published state data) is carried forward for all subsequent months:

$$
\hat{\theta}_{r, M}^{\text{prod}} = \begin{cases}
\theta_{r, M}^{\text{prod}} & \text{if } M_{s, M} \text{ is available for at least one state } s \in r \\
\hat{\theta}_{r, M-1}^{\text{prod}} & \text{otherwise (forward-fill)}
\end{cases}
$$

**Justification**: Regional production shares are structurally slow-moving. Appalachian Basin, Permian, and Haynesville production geographies do not shift dramatically quarter-to-quarter, making the constant-share extrapolation a reasonable approximation over lag periods of 1–2 years. The assumption is revisited automatically each time the pipeline is re-run as new EIA state-level data is published.

---

### 3. Regional Lease/Plant and Pipeline Fuel Downscaling
Lease/plant and pipeline fuel consumption represent self-consumption and transport losses within the gas system. They are downscaled from national monthly totals using distinct physical proxies:

#### A. Lease & Plant Fuel Downscaling
Lease and plant fuel consumption ($\text{L\&P Fuel}_{r, M}$) is strongly tied to physical gas extraction and processing. We therefore allocate the national monthly total ($\text{US L\&P}_M$, EIA Series `N9160US2`) using the regional dry production share:

$$
\text{Lease \& Plant Fuel}_{r, M} = \text{US L\&P}_M \times \theta_{r, M}^{\text{prod}}
$$

where $\theta_{r, M}^{\text{prod}}$ is the production allocation ratio defined in Section 2.

#### B. Pipeline Fuel Downscaling
Pipeline fuel consumption ($\text{Pipeline Fuel}_{r, M}$) represents the energy used to compress and transport gas through pipelines. This is driven by local consumption. We allocate the national monthly total ($\text{US Pipeline}_M$, EIA Series `N9170US2`) using the regional share of consumer deliveries:

$$
\text{Pipeline Fuel}_{r, M} = \text{US Pipeline}_M \times \theta_{r, M}^{\text{cons}}
$$

where the consumption allocation ratio $\theta_{r, M}^{\text{cons}}$ is defined as:

$$
\theta_{r, M}^{\text{cons}} = \frac{\text{Retail Consumption}_{r, M}}{\text{US Retail Consumption}_M}
$$

where:
*   $\text{Retail Consumption}_{r, M} = \text{ResCom}_{r, M} + \text{Power Burn}_{r, M} + \text{Industrial}_{r, M}$ is the total regional gas demand delivered to end-users.
*   $\text{US Retail Consumption}_M$ is the national monthly consumer deliveries (EIA Series `N9140US2`).

#### C. Total Regional Fuel Use
The total monthly regional fuel use is the sum of these two downscaled components:

$$
\text{Fuel Use}_{r, M} = \text{Lease \& Plant Fuel}_{r, M} + \text{Pipeline Fuel}_{r, M}
$$

---

### 4. Regional Citygate Pricing & Basis-Spread Projection
To capture regional basis risk (such as localized delivery capacity constraints and winter bottlenecks), the platform models regional electricity sector gas demand using state-level Citygate prices instead of national Henry Hub spot prices. This requires constructing a regional price index and projecting it to mitigate reporting lags.

#### A. Consumption-Weighted Regional Price Index
The regional Citygate price index ($P_{r, M}$) is constructed by weighting state-level Citygate prices by each state's total retail gas consumption. For each state $s$ in region $r$ and month $M$, we define total retail consumption $C_{s, M}$ as the sum of Residential, Commercial, Industrial, and Power Burn consumption:

$$
C_{s, M} = C^{\text{res}}_{s, M} + C^{\text{com}}_{s, M} + C^{\text{ind}}_{s, M} + C^{\text{power\_burn}}_{s, M}
$$

Using the state-level monthly Citygate price $P_{s, M}$ (EIA Series `N3050ST2`), the regional price index is computed as:

$$
P_{r, M} = \begin{cases} 
\frac{\sum_{s \in r} P_{s, M} \times C_{s, M}}{\sum_{s \in r} C_{s, M}} & \text{if } \sum_{s \in r} C_{s, M} > 0 \\
0.0 & \text{otherwise}
\end{cases}
$$

This consumption-weighted formulation ensures that major demand centers dominate the regional index, preventing low-consumption states from skewing the regional price signal.

#### B. Basis-Spread Projection Model (Lag Mitigation)
While spot prices are available daily, EIA state-level Citygate prices are published with an approximate 2-month reporting lag. To project regional prices in real-time and during forecasting windows, we model the regional price as a seasonal basis spread added to the daily-averaged weekly Henry Hub spot price.

1.  **Historical Basis Spread**:
    For each historical month $M$, the basis spread $B^{\text{spread}}_M$ is defined as:
    
    $$
    B^{\text{spread}}_M = P_{r, M} - P^{\text{HH}}_M
    $$
    
    where $P^{\text{HH}}_M$ is the monthly average Henry Hub Spot Price ($/MMBtu).
    
2.  **Seasonal Calendar Profile**:
    The historical average basis spread for each calendar month $m \in \{1, \dots, 12\}$ is computed over all available years:
    
    $$
    \bar{B}^{\text{spread}}_m = \frac{1}{|Y_m|} \sum_{M \in Y_m} B^{\text{spread}}_M
    $$
    
    where $Y_m$ is the set of historical periods matching calendar month $m$.

3.  **Weekly Price Projection**:
    For any given week $t$ falling in calendar month $m_t$, the weekly regional Citygate price $P_{r, t}$ is projected using the real-time average weekly Henry Hub price $P^{\text{HH}}_t$:
    
    $$
    P_{r, t} = P^{\text{HH}}_t + \bar{B}^{\text{spread}}_{m_t}
    $$
    
This projected regional price $P_{r, t}$ is used directly in the weekly Power Burn regression to capture localized price elasticities.

---

### 5. Ratio-to-Seasonal Profile Extrapolation
For weeks extending beyond the publication dates of monthly EIA statistics, we must extrapolate non-weather-sensitive components: **Dry Production**, **Industrial Demand**, and **Fuel Use** (collectively referred to as $col \in \{ \text{dry\_production}, \text{industrial}, \text{fuel\_use} \}$).

1.  **Daily Rate Conversion**: We convert historical monthly totals to daily rates:
    $$R_{col, M} = \frac{\text{Value}_{col, M}}{D_M}$$
2.  **Seasonal Profile Fitting**: We calculate the multi-year seasonal daily average rate for each calendar month $m \in \{1, \dots, 12\}$:
    $$S_{col, m} = \frac{1}{|Y_m|} \sum_{M \in Y_m} R_{col, M}$$
    where $Y_m$ is the set of monthly historical periods corresponding to calendar month $m$.
3.  **Trend Ratio Calculation**: We establish a scaling ratio $\theta_{col}$ using the last available historical month $M_{\text{last}}$ (with calendar month $m_{\text{last}}$):
    $$\theta_{col} = \frac{R_{col, M_{\text{last}}}}{S_{col, m_{\text{last}}}}$$
4.  **Temporal Reconstruction**:
    *   For dates $t$ falling within the historical monthly range (using the midpoint $c(M)$ of each month $M$ as the coordinate), we perform linear interpolation:
        $$\text{Daily Rate}_{col, t} = \text{LinearInterpolate}\Big(t, \big\{ (c(M), R_{col, M}) \big\}\Big)$$
    *   For out-of-range dates $t > c(M_{\text{last}})$ in the forecasting window, we apply the trend ratio to the monthly seasonal baseline:
        $$\text{Daily Rate}_{col, t} = S_{col, m_t} \times \theta_{col}$$
    where $m_t = \text{month}(t)$.
5.  **Weekly Aggregation**:
    $$\text{Weekly Value}_{col, t} = 7 \times \text{Daily Rate}_{col, t}$$
    
---

### 6. Market Tightness & 5-Year Centered Rolling Seasonal Average
Comparing raw supply-demand balances across multiple decades is misleading due to structural changes (e.g., the U.S. shale boom, which doubled national production over the last 15 years). To isolate the structural tightness of the market from these multi-year trends, we define the **Market Tightness** indicator.

**Forecasting boundary**: this centered statistic intentionally uses years on
both sides of a historical observation. It is an ex post analytical context
metric only, and it is not a feature in the default forecast model or a
recursive backtest input.

1.  **Seasonal Balance Norm**:
    For any week $t$, let $w_t = \text{week\_of\_year}(t)$ and $y_t = \text{year}(t)$. The seasonal baseline is computed as the rolling average of the local balance $B_{r, w_t, y}$ for the same week of the year, centered around the current year $y_t$ with a window of 5 years:
    
    $$
    \text{Seasonal Norm}_{r, t} = \frac{1}{|Y_{y_t, w_t}|} \sum_{y = y_t - 2}^{y_t + 2} B_{r, w_t, y}
    $$
    
    where:
    *   $B_{r, w_t, y}$ is the regional local balance $B_r = \text{Dry Production}_r - \text{Total Consumption}_r$ in week-of-year $w_t$ of year $y$.
    *   $Y_{y_t, w_t} = [y_t - 2, y_t + 2] \cap \{y \mid B_{r, w_t, y} \text{ exists}\}$ is the set of years for which data exists.
2.  **Market Tightness**:
    The market tightness $\tau_{r, t}$ is the contemporaneous deviation:
    
    $$
    \tau_{r, t} = B_{r, t} - \text{Seasonal Norm}_{r, t}
    $$
    
    *   A **negative** value indicates the market is **tight** (supply deficit relative to the historical seasonal norm of that era, typically drawing down storage or reducing exports, which is bullish for prices).
    *   A **positive** value indicates the market is **loose** (supply surplus, typically building storage or increasing exports, which is bearish for prices).
3.  **Rolling Trend**:
    A 5-week simple rolling average of market tightness is computed to filter short-term weather noise:
    
    $$
    \tau_{r, t}^{\text{rolling}} = \frac{1}{5} \sum_{k=0}^{4} \tau_{r, t-k}
    $$
    
---

### 7. Recursive Multi-Horizon Forecaster State Simulation
To project storage levels multiple weeks into the future, we run a recursive roll-forward simulation. Let the forecast horizon be $H$ weeks, starting at week $t=1$. The state of the system is updated week-by-week:

#### Input Availability
The default recursive mode creates target-week weather and optional local
balance inputs from seasonal profiles estimated only on rows before the
forecast origin. This is the operational-style evaluation. An explicit
observed-input diagnostic can substitute realized future weather or balance
values, but it is an oracle benchmark rather than a live forecast result.

#### A. Storage State Transition
The fundamental state transition equation is:

$$
S_t = S_{t-1} + \widehat{\Delta S}_t
$$

where:
*   $S_{t-1}$ is the storage level at the end of week $t-1$ (with initial state $S_0$ as the last actual storage level).
*   $\widehat{\Delta S}_t$ is the predicted storage change for week $t$:
    $$\widehat{\Delta S}_t = f(\mathbf{x}_t)$$
    where $f$ is the fitted machine learning model, and $\mathbf{x}_t$ is the feature vector constructed at week $t$.
    
#### B. Recursive Feature Construction
The feature vector $\mathbf{x}_t$ is updated dynamically at each step using the simulated states from previous steps:
*   **Storage Lags & Deviations**:
    *   $\text{weekly\_change\_lag1}_t = \widehat{\Delta S}_{t-1}$ (for $t=1$, this is the last actual change $\Delta S_0$).
    *   $\text{weekly\_change\_rolling\_4wk}_t = \frac{1}{4} \sum_{i=1}^4 \widehat{\Delta S}_{t-i}$
    *   $\text{storage\_vs\_5yr\_avg}_t = S_{t-1} - S^{\text{5yr\_avg}}_t$
    *   $\text{storage\_vs\_last\_year}_t = S_{t-1} - S^{\text{lag52}}_t$
*   **Balancing Inflow Lags**:
    The physical balance residual (representing pipeline border flows and net regional imports/exports) is:
    $$\widehat{I}_t = \widehat{\Delta S}_t - B_t$$
    where $B_t$ is the local supply-demand balance in week $t$ (derived from weather scenario projections or its historical seasonal average $\bar{B}(w_t)$).
    These simulate the balancing features:
    *   $\text{net\_inflow\_balancing\_lag1}_t = \widehat{I}_{t-1}$
    *   $\text{net\_inflow\_balancing\_rolling\_4wk}_t = \frac{1}{4} \sum_{i=1}^4 \widehat{I}_{t-i}$
    *   $\text{local\_balance\_lag1}_t = B_{t-1}$
    
#### C. Simulation Algorithm
For each week $t = 1, 2, \dots, H$ in the horizon:
1.  **Weather Scenario Adjustment**: Scale baseline temperature by anomaly $\Delta T$:
    $$T_t = T_t^{\text{base}} + \Delta T \implies \text{HDD}_t, \text{CDD}_t$$
2.  **Weather Feature Construction**: Compute $\text{HDD}_{t-1}$, $\text{CDD}_{t-1}$, and rolling 4-week weather averages.
3.  **Storage Deviations**: Compute current storage deviations from seasonal and year-ago norms:
    $$\text{dev}^{\text{5yr}}_t = S_{t-1} - S^{\text{5yr\_avg}}_t, \quad \text{dev}^{\text{year}}_t = S_{t-1} - S^{\text{lag52}}_t$$
4.  **Fetch Lagged States**: Gather recursive predictions for $\Delta S_{t-1}$ and physical inflows $I_{t-1}$.
5.  **Predict Change**: Predict $\widehat{\Delta S}_t = f(\mathbf{x}_t)$.
6.  **Update Storage State**: $S_t = S_{t-1} + \widehat{\Delta S}_t$.
7.  **Calculate Simulated Inflow**: $I_t = \widehat{\Delta S}_t - B_t$ (where $B_t$ is the local balance).
8.  **Propagate Lags**: Append states to history and proceed to week $t+1$.

---

### 8. Zero-Leakage Date-Based Expanding Window Splitter
Evaluating time-series forecasting models using standard K-fold cross-validation is invalid because it violates the chronological order of data, causing "temporal look-ahead leakage". To prevent this, we implement a **Zero-Leakage Date-Based Expanding Window Splitter**.

#### A. Mathematical Split Definition
Let $D$ be the set of all chronological weekly dates in our dataset. The splitter divides the data into multiple folds $k = 0, 1, \dots, K$.

1.  **Training Window ($T_k$)**:
    The training window for fold $k$ contains all observations whose dates $t$ satisfy:
    
    $$
    T_k = \{ t \in D \mid t_{\text{start}} \le t \le t_{\text{end}}^{(k)} \}
    $$
    
    where the start date $t_{\text{start}}$ is fixed (the beginning of the dataset), and the end date expands at each step:
    
    $$
    t_{\text{end}}^{(k)} = t_{\text{end}}^{(0)} + k \times \Delta_{\text{step}}
    $$
    
    where $t_{\text{end}}^{(0)}$ is the initial training end date, and $\Delta_{\text{step}}$ is the step size in weeks.
2.  **Validation Window ($V_k$)**:
    The validation window for fold $k$ contains all observations whose dates $t$ satisfy:
    
    $$
    V_k = \{ t \in D \mid v_{\text{start}}^{(k)} \le t \le v_{\text{end}}^{(k)} \}
    $$
    
    where the validation boundaries are defined strictly relative to the training boundaries:
    
    $$
    v_{\text{start}}^{(k)} = t_{\text{end}}^{(k)} + 1 \text{ day}
    $$
    
    $$
    v_{\text{end}}^{(k)} = v_{\text{start}}^{(k)} + \Delta_{\text{val\_weeks}} - 1 \text{ day}
    $$
    
    where $\Delta_{\text{val\_weeks}}$ is the length of the validation window in weeks.
    
#### B. Leakage Prevention
This structure guarantees:
*   **No Future Training Leakage**: Since $\min(V_k) > \max(T_k)$ for all $k$, the training set contains absolutely no observations from the validation period or beyond.
*   **Temporal Integrity**: The machine learning model is evaluated in a realistic setup: simulating the past by training only on data that would have been known *before* the validation window.
*   **No Overlapping Leakage**: Since validation windows are shifted by $\Delta_{\text{step}}$, we get multiple independent testing intervals, allowing robust estimation of average forecast performance over different market environments.

Date ordering alone does not establish input availability. Recursive evaluation
must also choose a target-week input mode; the default seasonal mode does so by
deriving weather and optional balance profiles from the fold history only.
