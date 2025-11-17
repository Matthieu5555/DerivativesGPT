"""
Barrier Option Pricing Implementation

Implements analytical formulas for barrier options using the Merton-Reiner approach.
Supports eight types of barrier options:
- Down-and-out (call/put)
- Down-and-in (call/put)
- Up-and-out (call/put)
- Up-and-in (call/put)

References:
- Merton, R.C. (1973). Theory of Rational Option Pricing
- Reiner, E. and Rubinstein, M. (1991). Breaking Down the Barriers
- Haug, E.G. (2007). The Complete Guide to Option Pricing Formulas
"""

import numpy as np
from scipy.stats import norm
from typing import Literal
import logging

logger = logging.getLogger(__name__)


def price_down_out_call(
    S: float,
    K: float,
    H: float,
    T: float,
    r: float,
    sigma: float,
    rebate: float = 0.0
) -> float:
    """
    Price a down-and-out call option.

    The option knocks out if the price touches or goes below the barrier H.

    Args:
        S: Current spot price
        K: Strike price
        H: Barrier level (must be <= min(S, K))
        T: Time to maturity in years
        r: Risk-free rate
        sigma: Volatility
        rebate: Payment if knocked out (default 0)

    Returns:
        Option price
    """
    # Barrier must be below current spot for down-and-out
    # Check this FIRST before checking if knocked out
    if H > S:
        raise ValueError(f"For down-and-out call, barrier {H} must be <= spot {S}")

    if S <= H:
        # Already knocked out (S == H case)
        return rebate * np.exp(-r * T)

    # Parameters
    mu = (r - 0.5 * sigma**2) / sigma**2
    lambda_val = np.sqrt(mu**2 + 2 * r / sigma**2)
    z = np.log(H**2 / (S * K)) / (sigma * np.sqrt(T)) + lambda_val * sigma * np.sqrt(T)

    # Components for down-and-out call
    x1 = np.log(S / K) / (sigma * np.sqrt(T)) + (1 + mu) * sigma * np.sqrt(T)
    x2 = np.log(S / H) / (sigma * np.sqrt(T)) + (1 + mu) * sigma * np.sqrt(T)
    y1 = np.log(H**2 / (S * K)) / (sigma * np.sqrt(T)) + (1 + mu) * sigma * np.sqrt(T)
    y2 = np.log(H / S) / (sigma * np.sqrt(T)) + (1 + mu) * sigma * np.sqrt(T)

    # Price calculation
    if K > H:
        # Standard case
        call_value = (S * norm.cdf(x1) - K * np.exp(-r * T) * norm.cdf(x1 - sigma * np.sqrt(T)) -
                     S * (H / S)**(2 * (mu + 1)) * norm.cdf(y1) +
                     K * np.exp(-r * T) * (H / S)**(2 * mu) * norm.cdf(y1 - sigma * np.sqrt(T)))
    else:
        # K <= H, option can never be exercised
        call_value = 0

    # Add rebate value if knocked out
    if rebate > 0:
        # Probability of hitting barrier
        eta = 1  # For down barrier
        phi = 1  # For call

        z1 = np.log(H / S) / (sigma * np.sqrt(T)) + lambda_val * sigma * np.sqrt(T)
        z2 = np.log(H / S) / (sigma * np.sqrt(T)) - lambda_val * sigma * np.sqrt(T)

        rebate_value = rebate * ((H / S)**(mu + lambda_val) * norm.cdf(eta * z1) +
                                 (H / S)**(mu - lambda_val) * norm.cdf(eta * z2))
        call_value += rebate_value

    return max(0, call_value)


def price_down_out_put(
    S: float,
    K: float,
    H: float,
    T: float,
    r: float,
    sigma: float,
    rebate: float = 0.0
) -> float:
    """Price a down-and-out put option."""
    if S <= H:
        return rebate * np.exp(-r * T)

    if H > K:
        raise ValueError(f"For down-and-out put, barrier {H} must be <= strike {K}")

    mu = (r - 0.5 * sigma**2) / sigma**2

    x1 = np.log(S / K) / (sigma * np.sqrt(T)) + (1 + mu) * sigma * np.sqrt(T)
    x2 = np.log(S / H) / (sigma * np.sqrt(T)) + (1 + mu) * sigma * np.sqrt(T)
    y1 = np.log(H**2 / (S * K)) / (sigma * np.sqrt(T)) + (1 + mu) * sigma * np.sqrt(T)
    y2 = np.log(H / S) / (sigma * np.sqrt(T)) + (1 + mu) * sigma * np.sqrt(T)

    if K > H:
        put_value = (-S * norm.cdf(-x1) + K * np.exp(-r * T) * norm.cdf(-x1 + sigma * np.sqrt(T)) +
                    S * (H / S)**(2 * (mu + 1)) * (norm.cdf(y2) - norm.cdf(y1)) -
                    K * np.exp(-r * T) * (H / S)**(2 * mu) *
                    (norm.cdf(y2 - sigma * np.sqrt(T)) - norm.cdf(y1 - sigma * np.sqrt(T))))
    else:
        # K <= H
        put_value = (-S * norm.cdf(-x2) + K * np.exp(-r * T) * norm.cdf(-x2 + sigma * np.sqrt(T)) +
                    S * (H / S)**(2 * (mu + 1)) * norm.cdf(y2) -
                    K * np.exp(-r * T) * (H / S)**(2 * mu) * norm.cdf(y2 - sigma * np.sqrt(T)))

    return max(0, put_value)


def price_up_out_call(
    S: float,
    K: float,
    H: float,
    T: float,
    r: float,
    sigma: float,
    rebate: float = 0.0
) -> float:
    """Price an up-and-out call option."""
    if H < max(S, K):
        raise ValueError(f"For up-and-out call, barrier {H} must be >= max(spot {S}, strike {K})")

    if S >= H:
        return rebate * np.exp(-r * T)

    # Use in-out parity: up-and-out call + up-and-in call = vanilla call
    from derivatives_gpt_core.features.vanilla.pricing import black_scholes_call

    vanilla_price = black_scholes_call(S, K, T, r, sigma)
    in_price = price_up_in_call(S, K, H, T, r, sigma, 0)

    return vanilla_price - in_price + rebate * np.exp(-r * T) * (S >= H)


def price_up_out_put(
    S: float,
    K: float,
    H: float,
    T: float,
    r: float,
    sigma: float,
    rebate: float = 0.0
) -> float:
    """Price an up-and-out put option."""
    if H < max(S, K):
        raise ValueError(f"For up-and-out put, barrier {H} must be >= max(spot {S}, strike {K})")

    if S >= H:
        return rebate * np.exp(-r * T)

    mu = (r - 0.5 * sigma**2) / sigma**2

    x1 = np.log(S / K) / (sigma * np.sqrt(T)) + (1 + mu) * sigma * np.sqrt(T)
    x2 = np.log(S / H) / (sigma * np.sqrt(T)) + (1 + mu) * sigma * np.sqrt(T)
    y1 = np.log(H**2 / (S * K)) / (sigma * np.sqrt(T)) + (1 + mu) * sigma * np.sqrt(T)
    y2 = np.log(H / S) / (sigma * np.sqrt(T)) + (1 + mu) * sigma * np.sqrt(T)

    if K < H:
        # Standard case
        put_value = (-S * norm.cdf(-x1) + K * np.exp(-r * T) * norm.cdf(-x1 + sigma * np.sqrt(T)) +
                    S * (H / S)**(2 * (mu + 1)) * norm.cdf(-y1) -
                    K * np.exp(-r * T) * (H / S)**(2 * mu) * norm.cdf(-y1 + sigma * np.sqrt(T)))
    else:
        # K >= H, option can never be exercised
        put_value = 0

    return max(0, put_value)


def price_down_in_call(
    S: float,
    K: float,
    H: float,
    T: float,
    r: float,
    sigma: float,
    rebate: float = 0.0
) -> float:
    """Price a down-and-in call option."""
    # Use in-out parity
    from derivatives_gpt_core.features.vanilla.pricing import black_scholes_call

    vanilla_price = black_scholes_call(S, K, T, r, sigma)
    out_price = price_down_out_call(S, K, H, T, r, sigma, 0)

    return vanilla_price - out_price


def price_down_in_put(
    S: float,
    K: float,
    H: float,
    T: float,
    r: float,
    sigma: float,
    rebate: float = 0.0
) -> float:
    """Price a down-and-in put option."""
    from derivatives_gpt_core.features.vanilla.pricing import black_scholes_put

    vanilla_price = black_scholes_put(S, K, T, r, sigma)
    out_price = price_down_out_put(S, K, H, T, r, sigma, 0)

    return vanilla_price - out_price


def price_up_in_call(
    S: float,
    K: float,
    H: float,
    T: float,
    r: float,
    sigma: float,
    rebate: float = 0.0
) -> float:
    """Price an up-and-in call option."""
    if S >= H:
        # Already knocked in, becomes vanilla
        from derivatives_gpt_core.features.vanilla.pricing import black_scholes_call
        return black_scholes_call(S, K, T, r, sigma)

    mu = (r - 0.5 * sigma**2) / sigma**2

    x1 = np.log(S / K) / (sigma * np.sqrt(T)) + (1 + mu) * sigma * np.sqrt(T)
    y1 = np.log(H**2 / (S * K)) / (sigma * np.sqrt(T)) + (1 + mu) * sigma * np.sqrt(T)

    if K < H:
        # Option only valuable if barrier is hit
        in_value = (S * (H / S)**(2 * (mu + 1)) * norm.cdf(y1) -
                   K * np.exp(-r * T) * (H / S)**(2 * mu) * norm.cdf(y1 - sigma * np.sqrt(T)))
    else:
        # K >= H, different formula
        x2 = np.log(S / H) / (sigma * np.sqrt(T)) + (1 + mu) * sigma * np.sqrt(T)
        y2 = np.log(H / S) / (sigma * np.sqrt(T)) + (1 + mu) * sigma * np.sqrt(T)

        in_value = (S * norm.cdf(x1) - K * np.exp(-r * T) * norm.cdf(x1 - sigma * np.sqrt(T)) -
                   S * norm.cdf(x2) + K * np.exp(-r * T) * norm.cdf(x2 - sigma * np.sqrt(T)) +
                   S * (H / S)**(2 * (mu + 1)) * norm.cdf(y2) -
                   K * np.exp(-r * T) * (H / S)**(2 * mu) * norm.cdf(y2 - sigma * np.sqrt(T)))

    return max(0, in_value)


def price_up_in_put(
    S: float,
    K: float,
    H: float,
    T: float,
    r: float,
    sigma: float,
    rebate: float = 0.0
) -> float:
    """Price an up-and-in put option."""
    from derivatives_gpt_core.features.vanilla.pricing import black_scholes_put

    vanilla_price = black_scholes_put(S, K, T, r, sigma)
    out_price = price_up_out_put(S, K, H, T, r, sigma, 0)

    return vanilla_price - out_price


def price_barrier_option(
    barrier_type: Literal["down-out", "down-in", "up-out", "up-in"],
    option_type: Literal["call", "put"],
    S: float,
    K: float,
    H: float,
    T: float,
    r: float,
    sigma: float,
    rebate: float = 0.0
) -> float:
    """
    Main entry point for barrier option pricing.

    Args:
        barrier_type: Type of barrier ("down-out", "down-in", "up-out", "up-in")
        option_type: Option type ("call" or "put")
        S: Current spot price
        K: Strike price
        H: Barrier level
        T: Time to maturity in years
        r: Risk-free rate
        sigma: Volatility
        rebate: Payment if knocked out (default 0)

    Returns:
        Option price
    """
    pricing_functions = {
        ("down-out", "call"): price_down_out_call,
        ("down-out", "put"): price_down_out_put,
        ("down-in", "call"): price_down_in_call,
        ("down-in", "put"): price_down_in_put,
        ("up-out", "call"): price_up_out_call,
        ("up-out", "put"): price_up_out_put,
        ("up-in", "call"): price_up_in_call,
        ("up-in", "put"): price_up_in_put,
    }

    pricing_func = pricing_functions.get((barrier_type, option_type))

    if not pricing_func:
        raise ValueError(f"Unknown barrier option type: {barrier_type} {option_type}")

    logger.info(f"Pricing {barrier_type} {option_type} with S={S:.2f}, K={K:.2f}, H={H:.2f}, "
               f"T={T:.3f}, r={r:.3%}, sigma={sigma:.2%}")

    price = pricing_func(S, K, H, T, r, sigma, rebate)

    logger.info(f"Barrier option price: ${price:.2f}")

    return price