"""Integration tests for NVDA ticker validation feature."""

import pytest
from unittest.mock import Mock, patch
from derivatives_gpt_core.graph_nodes.classify_intent import classify_user_intent
from derivatives_gpt_core.graph_state_schema import OptionPricingState, ClassificationResult
from langchain_core.messages import HumanMessage


class TestNVDATickerValidation:
    """Test NVDA ticker validation in classification node."""

    @patch('derivatives_gpt_core.graph_nodes.classify_intent.get_classification_llm')
    @patch('derivatives_gpt_core.graph_nodes.classify_intent.validate_ticker_exists')
    def test_nvda_validation_success(self, mock_validate, mock_get_llm):
        """Test that NVDA ticker passes validation."""
        # Mock LLM response
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = '''
        {
            "can_price": true,
            "product_type": "european_put",
            "features_detected": ["vanilla"],
            "asset_class": "equity",
            "response_type": "can_price",
            "reasoning": "European put option on NVDA with all required parameters",
            "ticker": "NVDA"
        }
        '''
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        # Mock ticker validation - NVDA exists
        mock_validate.return_value = {
            'exists': True,
            'name': 'NVIDIA Corporation',
            'asset_type': 'equity',
            'reason': ''
        }

        # Create state with NVDA query
        state = OptionPricingState(
            messages=[HumanMessage(content="Price a put on NVDA strike 450, 60 days")]
        )

        # Run classification
        result = classify_user_intent(state)

        # Verify classification passed
        assert result['can_price'] is True
        assert result['product_type'] == 'european_put'
        assert result['extracted_ticker'] == 'NVDA'
        assert result['validation_failed'] is False
        assert result['response_type'] == 'can_price'

        # Verify ticker validation was called
        mock_validate.assert_called_once_with('NVDA')

        print("✓ NVDA ticker validation passed")

    @patch('derivatives_gpt_core.graph_nodes.classify_intent.get_classification_llm')
    @patch('derivatives_gpt_core.graph_nodes.classify_intent.validate_ticker_exists')
    def test_invalid_ticker_rejection(self, mock_validate, mock_get_llm):
        """Test that invalid tickers are rejected with friendly error."""
        # Mock LLM response
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = '''
        {
            "can_price": true,
            "product_type": "european_call",
            "features_detected": ["vanilla"],
            "asset_class": "equity",
            "response_type": "can_price",
            "reasoning": "European call option with all parameters",
            "ticker": "FAKE123"
        }
        '''
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        # Mock ticker validation - FAKE123 doesn't exist
        mock_validate.return_value = {
            'exists': False,
            'name': '',
            'asset_type': 'unknown',
            'reason': 'Ticker not found on Yahoo Finance'
        }

        # Create state with fake ticker query
        state = OptionPricingState(
            messages=[HumanMessage(content="Price a call on FAKE123 strike 100")]
        )

        # Run classification
        result = classify_user_intent(state)

        # Verify classification was overridden
        assert result['can_price'] is False
        assert result['response_type'] == 'clarify'
        assert result['validation_failed'] is True
        assert result['extracted_ticker'] == 'FAKE123'
        assert 'FAKE123' in result['reasoning']
        assert "couldn't find" in result['reasoning'].lower()

        # Verify ticker validation was called
        mock_validate.assert_called_once_with('FAKE123')

        print("✓ Invalid ticker properly rejected")

    @patch('derivatives_gpt_core.graph_nodes.classify_intent.get_classification_llm')
    def test_no_ticker_skips_validation(self, mock_get_llm):
        """Test that queries without tickers don't trigger validation."""
        # Mock LLM response - no ticker
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = '''
        {
            "can_price": false,
            "product_type": "unclear",
            "features_detected": [],
            "asset_class": "equity",
            "response_type": "clarify",
            "reasoning": "Missing ticker symbol",
            "ticker": null
        }
        '''
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        # Create state without ticker
        state = OptionPricingState(
            messages=[HumanMessage(content="Price an option")]
        )

        # Run classification
        result = classify_user_intent(state)

        # Verify classification
        assert result['can_price'] is False
        assert result['response_type'] == 'clarify'
        assert result['extracted_ticker'] is None
        assert result['validation_failed'] is False  # Validation wasn't triggered

        print("✓ No validation for queries without ticker")

    @patch('derivatives_gpt_core.graph_nodes.classify_intent.get_classification_llm')
    @patch('derivatives_gpt_core.graph_nodes.classify_intent.validate_ticker_exists')
    def test_multiple_tickers_all_validated(self, mock_validate, mock_get_llm):
        """Test that various tickers all get validated properly."""
        test_tickers = [
            ('NVDA', 'NVIDIA Corporation', True),
            ('AAPL', 'Apple Inc.', True),
            ('TSLA', 'Tesla, Inc.', True),
            ('META', 'Meta Platforms, Inc.', True),
            ('AMD', 'Advanced Micro Devices, Inc.', True),
        ]

        for ticker, name, expected_exists in test_tickers:
            # Mock LLM response
            mock_llm = Mock()
            mock_response = Mock()
            mock_response.content = f'''
            {{
                "can_price": true,
                "product_type": "european_call",
                "features_detected": ["vanilla"],
                "asset_class": "equity",
                "response_type": "can_price",
                "reasoning": "European call option",
                "ticker": "{ticker}"
            }}
            '''
            mock_llm.invoke.return_value = mock_response
            mock_get_llm.return_value = mock_llm

            # Mock ticker validation
            mock_validate.return_value = {
                'exists': expected_exists,
                'name': name if expected_exists else '',
                'asset_type': 'equity' if expected_exists else 'unknown',
                'reason': '' if expected_exists else 'Not found'
            }

            # Create state
            state = OptionPricingState(
                messages=[HumanMessage(content=f"Price a call on {ticker}")]
            )

            # Run classification
            result = classify_user_intent(state)

            # Verify
            assert result['can_price'] == expected_exists
            assert result['extracted_ticker'] == ticker
            assert result['validation_failed'] == (not expected_exists)

            print(f"✓ {ticker}: validation {'passed' if expected_exists else 'failed'} as expected")


class TestTickerValidationErrorMessages:
    """Test that ticker validation error messages are user-friendly."""

    @patch('derivatives_gpt_core.graph_nodes.classify_intent.get_classification_llm')
    @patch('derivatives_gpt_core.graph_nodes.classify_intent.validate_ticker_exists')
    def test_friendly_error_message(self, mock_validate, mock_get_llm):
        """Test that error messages are helpful to users."""
        # Mock LLM response
        mock_llm = Mock()
        mock_response = Mock()
        mock_response.content = '''
        {
            "can_price": true,
            "product_type": "european_put",
            "features_detected": ["vanilla"],
            "asset_class": "equity",
            "response_type": "can_price",
            "reasoning": "European put option",
            "ticker": "INVALIDTICKER"
        }
        '''
        mock_llm.invoke.return_value = mock_response
        mock_get_llm.return_value = mock_llm

        # Mock ticker validation
        mock_validate.return_value = {
            'exists': False,
            'name': '',
            'asset_type': 'unknown',
            'reason': 'Ticker not found on Yahoo Finance'
        }

        # Create state
        state = OptionPricingState(
            messages=[HumanMessage(content="Price a put on INVALIDTICKER")]
        )

        # Run classification
        result = classify_user_intent(state)

        # Check error message quality
        reasoning = result['reasoning']
        assert 'INVALIDTICKER' in reasoning
        assert 'Yahoo Finance' in reasoning
        assert 'finance.yahoo.com' in reasoning
        assert "couldn't find" in reasoning.lower() or "not found" in reasoning.lower()

        print(f"✓ Friendly error message: {reasoning}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
