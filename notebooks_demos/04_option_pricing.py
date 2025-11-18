
# %%
import sys
from pathlib import Path
import os

if '__file__' in globals():
    notebook_dir = Path(__file__).parent
    project_root = notebook_dir.parent
else:
    # Running in Jupyter - find project root by marker file
    current = Path(os.getcwd())
    project_root = current if (current / 'pyproject.toml').exists() else current.parent

sys.path.insert(0, str(project_root))

from derivatives_gpt_core.langchain_tools.black_scholes_tool import price_european_option
from derivatives_gpt_core.langchain_tools.american_option_tool import price_american_option
from derivatives_gpt_core.langchain_tools.geometric_asian_tool import price_geometric_asian_option
from derivatives_gpt_core.langchain_tools.digital_option_tool import price_digital_option

import inspect

# %%
# Direct tool invocation
result = price_european_option.invoke({
    "spot_price": 100,
    "strike_price": 105,
    "time_to_expiry_days": 90,  # 3 months
    "risk_free_rate": 0.05,
    "volatility": 0.2,
    "option_type": "call"
})
print(f"European Call Price: ${result}")

# %%
# American options can be exercised early
american_result = price_american_option.invoke({
    "spot_price": 100,
    "strike_price": 105,
    "time_to_expiry_days": 90,
    "risk_free_rate": 0.05,
    "volatility": 0.2,
    "option_type": "put",  # Put option
    "dividend_yield": 0.0
})
print(f"American Put Price: ${american_result}")

# %%
# Asian option (path-dependent)
asian_result = price_geometric_asian_option.invoke({
    "spot_price": 100,
    "strike_price": 105,
    "time_to_expiry_days": 90,
    "risk_free_rate": 0.05,
    "volatility": 0.2,
    "option_type": "call",
    "num_observations": 252  # Daily observations
}) 
print(f"Geometric Asian Call Price: ${asian_result}")

# Digital/Binary option
digital_result = price_digital_option.invoke({
    "spot_price": 100,
    "strike_price": 105,
    "time_to_expiry_days": 90,
    "risk_free_rate": 0.05,
    "volatility": 0.2,
    "option_type": "call",
    "payout": 1.0
})
print(f"Digital Call Price: ${digital_result}")

# %%
# Price multiple options with different strikes
print("Pricing call options across different strikes...\n")

strikes = [95, 100, 105, 110]
results = []

for strike in strikes:
    price = price_european_option.invoke({
        "spot_price": 100,
        "strike_price": strike,
        "time_to_expiry_days": 30,
        "risk_free_rate": 0.05,
        "volatility": 0.2,
        "option_type": "call"
    })
    results.append(price)

print("Portfolio Pricing Results (different strikes):")
for strike, price in zip(strikes, results):
    moneyness = "ITM" if strike < 100 else ("ATM" if strike == 100 else "OTM")
    print(f"  Strike ${strike:3d} ({moneyness}): ${price:.2f}")