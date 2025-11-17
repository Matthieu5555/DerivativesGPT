"""Utilities for option pricing demonstrations."""

from typing import Dict
import numpy as np
from derivatives_gpt_core.features.vanilla.pricing import price_european_option, calculate_greeks
from derivatives_gpt_core.features.american.pricing import price_american_option
from derivatives_gpt_core.features.barrier.pricing import price_barrier_option

def price_vanilla_options(spot: float, strike: float, time_to_expiry: float,
                         volatility: float, risk_free_rate: float) -> Dict:
    """Price European and American options."""

    # European Call
    euro_call = price_european_option(
        S=spot, K=strike, T=time_to_expiry,
        r=risk_free_rate, sigma=volatility, is_call=True
    )

    # European Put
    euro_put = price_european_option(
        S=spot, K=strike, T=time_to_expiry,
        r=risk_free_rate, sigma=volatility, is_call=False
    )

    # American Call
    amer_call = price_american_option(
        S=spot, K=strike, T=time_to_expiry,
        r=risk_free_rate, sigma=volatility,
        is_call=True, n_steps=100
    )

    # American Put
    amer_put = price_american_option(
        S=spot, K=strike, T=time_to_expiry,
        r=risk_free_rate, sigma=volatility,
        is_call=False, n_steps=100
    )

    return {
        'european_call': euro_call,
        'european_put': euro_put,
        'american_call': amer_call,
        'american_put': amer_put,
        'early_exercise_premium_call': amer_call - euro_call,
        'early_exercise_premium_put': amer_put - euro_put
    }

def price_barrier_options(spot: float, strike: float, barrier: float,
                         time_to_expiry: float, volatility: float,
                         risk_free_rate: float) -> Dict:
    """Price barrier options."""

    results = {}

    # Down-and-out call
    if barrier < spot:
        results['down_out_call'] = price_barrier_option(
            barrier_type='down_out_call',
            S=spot, K=strike, H=barrier,
            T=time_to_expiry, r=risk_free_rate, sigma=volatility
        )

    # Up-and-out call
    if barrier > spot:
        results['up_out_call'] = price_barrier_option(
            barrier_type='up_out_call',
            S=spot, K=strike, H=barrier,
            T=time_to_expiry, r=risk_free_rate, sigma=volatility
        )

    # Compare with vanilla
    vanilla_call = price_european_option(
        S=spot, K=strike, T=time_to_expiry,
        r=risk_free_rate, sigma=volatility, is_call=True
    )

    for barrier_type, price in results.items():
        results[f'{barrier_type}_discount'] = (vanilla_call - price) / vanilla_call * 100

    results['vanilla_call'] = vanilla_call

    return results

def calculate_option_greeks(spot: float, strike: float, time_to_expiry: float,
                           volatility: float, risk_free_rate: float,
                           is_call: bool = True) -> Dict:
    """Calculate all Greeks for an option."""

    greeks = calculate_greeks(
        S=spot, K=strike, T=time_to_expiry,
        r=risk_free_rate, sigma=volatility,
        is_call=is_call
    )

    return {
        'delta': greeks['delta'],
        'gamma': greeks['gamma'],
        'theta': greeks['theta'],
        'vega': greeks['vega'],
        'rho': greeks['rho']
    }

def generate_payoff_data(option_type: str, strike: float, premium: float,
                        spot_range: tuple = None) -> Dict:
    """Generate payoff data for charting."""

    if spot_range is None:
        spot_range = (strike * 0.7, strike * 1.3)

    spots = np.linspace(spot_range[0], spot_range[1], 100)

    if 'call' in option_type.lower():
        payoffs = np.maximum(spots - strike, 0) - premium
    else:
        payoffs = np.maximum(strike - spots, 0) - premium

    breakeven = strike + premium if 'call' in option_type.lower() else strike - premium

    return {
        'spot_prices': spots.tolist(),
        'payoffs': payoffs.tolist(),
        'breakeven': breakeven,
        'max_loss': -premium,
        'strike': strike
    }