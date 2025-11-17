"""
Test suite for exotic derivatives classification.

Ensures the system properly recognizes derivatives products even when
it cannot price them, setting appropriate response_type and extracting
all identifiable features.
"""

import pytest
from typing import Dict, Any


class TestExoticDerivativesRecognition:
    """Test that exotic derivatives are properly classified as recognize_but_refuse."""
    
    def test_asian_option_recognition(self):
        """Asian options should be recognized with averaging features detected."""
        query = "Price an Asian call option on AAPL with arithmetic average, strike 150, 90 days"
        
        expected = {
            "can_price": False,
            "response_type": "recognize_but_refuse",
            "product_type": "asian_option",
            "features_detected": ["path_dependent", "arithmetic_average", "averaging_period"],
            "asset_class": "equity_option",
            "option_type": "call",
            "strike_price": 150.0,
            "time_to_expiry_days": 90.0,
            "ticker": "AAPL"
        }
        
        # result = classify_user_intent(query)
        # assert result["can_price"] is False
        # assert result["response_type"] == "recognize_but_refuse"
        # assert "path_dependent" in result["features_detected"]
        # assert "asian" in result["product_type"].lower()
        
    def test_barrier_option_recognition(self):
        """Barrier options should extract barrier level and type."""
        query = "Calculate knock-out call on SPY, strike 400, barrier 450, 60 days"
        
        expected = {
            "can_price": False,
            "response_type": "recognize_but_refuse",
            "product_type": "barrier_option",
            "features_detected": ["knock_out", "up_and_out", "barrier_level"],
            "asset_class": "equity_option",
            "option_type": "call",
            "strike_price": 400.0,
            "time_to_expiry_days": 60.0,
            "ticker": "SPY",
            "reasoning": "Barrier option with knock-out feature - requires Monte Carlo with barrier monitoring"
        }
        
    def test_lookback_option_recognition(self):
        """Lookback options should be identified as path-dependent."""
        query = "Price a lookback put on TSLA expiring in 3 months"
        
        expected = {
            "can_price": False,
            "response_type": "recognize_but_refuse",
            "product_type": "lookback_option",
            "features_detected": ["path_dependent", "extreme_value", "lookback_period"],
            "asset_class": "equity_option",
            "option_type": "put",
            "time_to_expiry_days": 90.0,
            "ticker": "TSLA"
        }
        
    def test_variance_swap_recognition(self):
        """Variance swaps are volatility derivatives, not standard options."""
        query = "What's the fair variance swap rate on NVDA for 6 months?"
        
        expected = {
            "can_price": False,
            "response_type": "recognize_but_refuse",
            "product_type": "variance_swap",
            "features_detected": ["volatility_derivative", "realized_variance", "swap"],
            "asset_class": "volatility",
            "ticker": "NVDA",
            "time_to_expiry_days": 180.0
        }
        
    def test_rainbow_option_recognition(self):
        """Multi-asset options should be recognized with correlation dependency."""
        query = "Price a rainbow option on best of AAPL, MSFT, GOOGL, strike 100"
        
        expected = {
            "can_price": False,
            "response_type": "recognize_but_refuse",
            "product_type": "rainbow_option",
            "features_detected": ["multi_asset", "best_of", "correlation_dependent"],
            "asset_class": "equity_option",
            "strike_price": 100.0,
            "reasoning": "Multi-asset derivative requires correlation matrix and multi-dimensional pricing"
        }
        
    def test_compound_option_recognition(self):
        """Compound options (options on options) should be identified."""
        query = "Calculate a call on call option for IBM, strike 140, compound strike 5"
        
        expected = {
            "can_price": False,
            "response_type": "recognize_but_refuse",
            "product_type": "compound_option",
            "features_detected": ["second_order_derivative", "call_on_call", "two_strike_levels"],
            "asset_class": "equity_option",
            "ticker": "IBM",
            "strike_price": 140.0
        }
        
    def test_chooser_option_recognition(self):
        """Chooser options allow holder to choose call or put later."""
        query = "Value a chooser option on AMZN, choose in 30 days, expire 90 days, strike 150"
        
        expected = {
            "can_price": False,
            "response_type": "recognize_but_refuse",
            "product_type": "chooser_option",
            "features_detected": ["choice_period", "deferred_type_selection"],
            "asset_class": "equity_option",
            "ticker": "AMZN",
            "strike_price": 150.0,
            "time_to_expiry_days": 90.0
        }


class TestCreditDerivativesRecognition:
    """Test recognition of credit derivatives."""
    
    def test_cds_recognition(self):
        """Credit default swaps should be recognized."""
        query = "What's the CDS spread on Tesla corporate bonds, 5 year protection"
        
        expected = {
            "can_price": False,
            "response_type": "recognize_but_refuse",
            "product_type": "credit_default_swap",
            "features_detected": ["credit_derivative", "default_protection", "spread"],
            "asset_class": "credit",
            "ticker": "TSLA",
            "time_to_expiry_days": 1825.0  # 5 years
        }
        
    def test_cdo_recognition(self):
        """CDOs should be recognized as structured credit products."""
        query = "Price the senior tranche of a CDO on mortgage-backed securities"
        
        expected = {
            "can_price": False,
            "response_type": "recognize_but_refuse",
            "product_type": "collateralized_debt_obligation",
            "features_detected": ["structured_credit", "tranche", "credit_correlation"],
            "asset_class": "credit"
        }


class TestInterestRateExotics:
    """Test recognition of exotic interest rate derivatives."""
    
    def test_range_accrual_recognition(self):
        """Range accrual notes should be recognized."""
        query = "Value a range accrual note, accrues if SOFR stays between 4% and 5%, 2 years"
        
        expected = {
            "can_price": False,
            "response_type": "recognize_but_refuse",
            "product_type": "range_accrual",
            "features_detected": ["path_dependent", "conditional_accrual", "rate_range"],
            "asset_class": "interest_rate",
            "time_to_expiry_days": 730.0
        }
        
    def test_cms_spread_option_recognition(self):
        """CMS spread options should be recognized."""
        query = "Price a CMS spread option, 10y-2y spread, strike 50bp, 1 year"
        
        expected = {
            "can_price": False,
            "response_type": "recognize_but_refuse",
            "product_type": "cms_spread_option",
            "features_detected": ["yield_curve", "spread_option", "constant_maturity_swap"],
            "asset_class": "interest_rate",
            "time_to_expiry_days": 365.0
        }


class TestFeatureExtraction:
    """Test that features are properly extracted even when can_price=False."""
    
    def test_barrier_level_extraction(self):
        """Barrier levels should be extracted and stored."""
        query = "Knock-in call on NFLX, strike 500, barrier 550, 45 days"
        
        # Even though unpriceable, should extract:
        # - strike_price: 500.0
        # - barrier_level: 550.0 (if added to schema)
        # - barrier_type: "knock_in", "up_and_in"
        # - option_type: "call"
        # - time_to_expiry_days: 45.0
        pass
        
    def test_averaging_period_extraction(self):
        """Asian option averaging periods should be extracted."""
        query = "Asian put on GOOGL, geometric average over last 30 days, strike 2800"
        
        # Should extract:
        # - averaging_type: "geometric"
        # - averaging_period: 30.0
        # - averaging_timing: "trailing" or "lookback"
        pass
        
    def test_multiple_tickers_extraction(self):
        """Multi-asset derivatives should extract all tickers."""
        query = "Basket option on AAPL, MSFT, GOOGL equally weighted, strike 100"
        
        # Should extract:
        # - tickers: ["AAPL", "MSFT", "GOOGL"]
        # - weights: [0.333, 0.333, 0.333]
        # - basket_type: "equally_weighted"
        pass


class TestResponseMessaging:
    """Test that appropriate messages are generated for exotic derivatives."""
    
    def test_recognize_but_refuse_explains_why(self):
        """Response should explain why the product can't be priced."""
        query = "Price an Asian option on SPY"
        
        # Expected response message should include:
        # - Recognition: "I recognize this as an Asian option..."
        # - Limitation: "...but cannot price it because..."
        # - Reason: "...requires path-dependent pricing models not yet implemented"
        # - Features identified: "I detected: [arithmetic average, path dependent]"
        pass
        
    def test_suggest_alternatives_for_similar_products(self):
        """Should suggest priceable alternatives when possible."""
        query = "Calculate barrier option on AAPL"
        
        # Expected response should suggest:
        # - "I can price standard European call/put options on AAPL"
        # - "Would you like to price a European option instead?"
        pass


class TestEdgeCases:
    """Test edge cases in exotic derivative classification."""
    
    def test_ambiguous_exotic_vs_standard(self):
        """Handle queries that could be either standard or exotic."""
        query = "Price an option on AAPL, average strike"
        
        # "average strike" could mean:
        # 1. Asian option with average strike (exotic)
        # 2. Typo for "at average strike price" (standard)
        # Should clarify with user
        expected = {
            "response_type": "clarify",
            "reasoning": "Ambiguous: could be Asian option (average strike) or standard option at average price"
        }
        
    def test_exotic_feature_on_standard_product(self):
        """User might request exotic feature on standard product."""
        query = "Price European call on AAPL but with barrier at 200"
        
        # This is actually a barrier option, not European
        expected = {
            "can_price": False,
            "response_type": "recognize_but_refuse",
            "product_type": "barrier_option",
            "reasoning": "Adding barrier feature makes this an exotic derivative, not standard European"
        }
        
    def test_partial_exotic_information(self):
        """Handle queries with incomplete exotic specifications."""
        query = "Price a barrier option on TSLA strike 250"
        
        # Missing: barrier level, barrier type (knock-in/out)
        expected = {
            "response_type": "clarify",
            "missing_parameters": ["barrier_level", "barrier_type"],
            "reasoning": "Barrier options require barrier level and type (knock-in or knock-out)"
        }


# Integration test data structure
EXOTIC_CLASSIFICATION_TEST_CASES = [
    {
        "query": "Asian call on AAPL, arithmetic average, strike 150, 90 days",
        "expected_product_type": "asian_option",
        "expected_can_price": False,
        "expected_features": ["path_dependent", "arithmetic_average"]
    },
    {
        "query": "Barrier option knock-out call SPY strike 400 barrier 450",
        "expected_product_type": "barrier_option",
        "expected_can_price": False,
        "expected_features": ["knock_out", "barrier_level"]
    },
    {
        "query": "Lookback put on TSLA 3 months",
        "expected_product_type": "lookback_option",
        "expected_can_price": False,
        "expected_features": ["path_dependent", "extreme_value"]
    },
    {
        "query": "Variance swap on NVDA 6 months",
        "expected_product_type": "variance_swap",
        "expected_can_price": False,
        "expected_features": ["volatility_derivative", "realized_variance"]
    },
    {
        "query": "Rainbow option best of AAPL MSFT GOOGL strike 100",
        "expected_product_type": "rainbow_option",
        "expected_can_price": False,
        "expected_features": ["multi_asset", "best_of", "correlation_dependent"]
    },
    {
        "query": "Compound option call on call IBM strike 140",
        "expected_product_type": "compound_option",
        "expected_can_price": False,
        "expected_features": ["second_order_derivative", "call_on_call"]
    },
    {
        "query": "CDS spread on TSLA 5 year protection",
        "expected_product_type": "credit_default_swap",
        "expected_can_price": False,
        "expected_features": ["credit_derivative", "default_protection"]
    },
    {
        "query": "Range accrual SOFR between 4-5% for 2 years",
        "expected_product_type": "range_accrual",
        "expected_can_price": False,
        "expected_features": ["path_dependent", "conditional_accrual"]
    }
]


if __name__ == "__main__":
    print("Exotic Derivatives Classification Test Suite")
    print("=" * 60)
    print(f"Total test cases: {len(EXOTIC_CLASSIFICATION_TEST_CASES)}")
    print("\nTest categories:")
    print("- Path-dependent options (Asian, Lookback, Barrier)")
    print("- Multi-asset options (Rainbow, Basket)")
    print("- Second-order derivatives (Compound, Chooser)")
    print("- Volatility products (Variance swaps)")
    print("- Credit derivatives (CDS, CDO)")
    print("- Exotic interest rate products (Range accruals, CMS)")
    print("\nRun with: pytest test_exotic_classification.py -v")
