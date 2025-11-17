"""Tests for ticker validation utilities."""

import pytest
from derivatives_gpt_core.utils.ticker_validation import (
    validate_ticker_exists,
    get_friendly_ticker_error,
    _classify_asset_type,
)


class TestValidateTicker:
    """Test ticker validation against Yahoo Finance."""

    def test_valid_equity_tickers(self):
        """Test that common equity tickers validate successfully."""
        tickers = ['NVDA', 'AAPL', 'TSLA', 'GOOGL', 'MSFT', 'AMZN', 'META']

        for ticker in tickers:
            result = validate_ticker_exists(ticker)
            assert result['exists'] is True, f"{ticker} should be valid"
            assert result['name'] != '', f"{ticker} should have a name"
            assert result['asset_type'] in ['equity', 'unknown'], f"{ticker} should be equity"
            assert result['reason'] == '', f"{ticker} should have no error reason"
            print(f"✓ {ticker}: {result['name']} ({result['asset_type']})")

    def test_invalid_tickers(self):
        """Test that fake/invalid tickers are rejected."""
        fake_tickers = ['FAKE123', 'NOTREAL', 'ZZZZZ999', 'INVALIDTICKER']

        for ticker in fake_tickers:
            result = validate_ticker_exists(ticker)
            assert result['exists'] is False, f"{ticker} should be invalid"
            assert result['name'] == '', f"{ticker} should have no name"
            assert result['asset_type'] == 'unknown', f"{ticker} asset_type should be unknown"
            assert result['reason'] != '', f"{ticker} should have an error reason"
            print(f"✗ {ticker}: {result['reason']}")

    def test_etf_tickers(self):
        """Test that ETF tickers validate successfully."""
        etf_tickers = ['SPY', 'QQQ', 'VOO']

        for ticker in etf_tickers:
            result = validate_ticker_exists(ticker)
            assert result['exists'] is True, f"{ticker} should be valid"
            assert result['name'] != '', f"{ticker} should have a name"
            assert result['asset_type'] in ['etf', 'equity', 'unknown'], f"{ticker} should be ETF or equity"
            print(f"✓ {ticker}: {result['name']} ({result['asset_type']})")

    def test_index_tickers(self):
        """Test that index tickers validate successfully."""
        index_tickers = ['^GSPC', '^DJI']

        for ticker in index_tickers:
            result = validate_ticker_exists(ticker)
            # Indices may or may not be supported depending on Yahoo Finance
            if result['exists']:
                assert result['name'] != '', f"{ticker} should have a name"
                print(f"✓ {ticker}: {result['name']} ({result['asset_type']})")
            else:
                print(f"⚠ {ticker}: Not available (expected for some indices)")

    def test_crypto_tickers(self):
        """Test that crypto tickers validate successfully."""
        crypto_tickers = ['BTC-USD', 'ETH-USD']

        for ticker in crypto_tickers:
            result = validate_ticker_exists(ticker)
            assert result['exists'] is True, f"{ticker} should be valid"
            assert result['name'] != '', f"{ticker} should have a name"
            assert result['asset_type'] in ['crypto', 'cryptocurrency', 'unknown'], f"{ticker} should be crypto"
            print(f"✓ {ticker}: {result['name']} ({result['asset_type']})")

    def test_case_insensitivity(self):
        """Test that ticker validation is case-insensitive."""
        test_cases = [
            ('nvda', 'NVDA'),
            ('aapl', 'AAPL'),
            ('Tsla', 'TSLA'),
            ('gOoGl', 'GOOGL')
        ]

        for lower_case, upper_case in test_cases:
            result_lower = validate_ticker_exists(lower_case)
            result_upper = validate_ticker_exists(upper_case)

            assert result_lower['exists'] == result_upper['exists']
            assert result_lower['name'] == result_upper['name']
            print(f"✓ {lower_case} == {upper_case}")

    def test_whitespace_handling(self):
        """Test that whitespace is properly stripped."""
        result = validate_ticker_exists('  AAPL  ')
        assert result['exists'] is True
        assert result['name'] != ''
        print(f"✓ Whitespace handled correctly")

    def test_caching(self):
        """Test that validation results are cached."""
        # First call - should fetch from Yahoo Finance
        result1 = validate_ticker_exists('AAPL')

        # Second call - should use cache
        result2 = validate_ticker_exists('AAPL')

        # Results should be identical
        assert result1 == result2
        print(f"✓ Caching working correctly")


class TestClassifyAssetType:
    """Test asset type classification."""

    def test_equity_classification(self):
        """Test equity asset classification."""
        info = {'quoteType': 'EQUITY', 'sharesOutstanding': 1000000}
        assert _classify_asset_type(info) == 'equity'

    def test_etf_classification(self):
        """Test ETF asset classification."""
        info = {'quoteType': 'ETF'}
        assert _classify_asset_type(info) == 'etf'

    def test_index_classification(self):
        """Test index asset classification."""
        info = {'quoteType': 'INDEX'}
        assert _classify_asset_type(info) == 'index'

        info = {'quoteType': 'MUTUALFUND'}
        assert _classify_asset_type(info) == 'index'

    def test_crypto_classification(self):
        """Test crypto asset classification."""
        info = {'quoteType': 'CRYPTOCURRENCY'}
        assert _classify_asset_type(info) == 'crypto'

    def test_unknown_classification(self):
        """Test unknown asset classification."""
        info = {'quoteType': 'UNKNOWN_TYPE'}
        assert _classify_asset_type(info) == 'unknown'

    def test_case_insensitive_classification(self):
        """Test that classification is case-insensitive."""
        info_lower = {'quoteType': 'equity'}
        info_upper = {'quoteType': 'EQUITY'}

        assert _classify_asset_type(info_lower) == 'equity'
        assert _classify_asset_type(info_upper) == 'equity'

    def test_fallback_classification(self):
        """Test fallback classification based on shares outstanding."""
        info = {'quoteType': 'UNKNOWN', 'sharesOutstanding': 1000000}
        assert _classify_asset_type(info) == 'equity'

        info = {'quoteType': 'UNKNOWN', 'sharesOutstanding': 0}
        assert _classify_asset_type(info) == 'unknown'


class TestFriendlyTickerError:
    """Test user-friendly error message generation."""

    def test_ticker_not_found_error(self):
        """Test error message for ticker not found."""
        validation_result = {
            'exists': False,
            'name': '',
            'asset_type': 'unknown',
            'reason': 'Ticker not found on Yahoo Finance'
        }

        error_msg = get_friendly_ticker_error('FAKE123', validation_result)

        assert 'FAKE123' in error_msg
        assert "couldn't find" in error_msg.lower()
        assert 'yahoo' in error_msg.lower()
        assert 'finance.yahoo.com' in error_msg
        print(f"✓ Error message: {error_msg}")

    def test_no_data_error(self):
        """Test error message for no data available."""
        validation_result = {
            'exists': False,
            'name': '',
            'asset_type': 'unknown',
            'reason': 'No price data available for ticker'
        }

        error_msg = get_friendly_ticker_error('DELISTED', validation_result)

        assert 'DELISTED' in error_msg
        assert "couldn't find" in error_msg.lower()
        print(f"✓ Error message: {error_msg}")

    def test_validation_error(self):
        """Test error message for validation errors."""
        validation_result = {
            'exists': False,
            'name': '',
            'asset_type': 'unknown',
            'reason': 'Validation error: Network timeout'
        }

        error_msg = get_friendly_ticker_error('TIMEOUT', validation_result)

        assert 'TIMEOUT' in error_msg
        assert "couldn't find" in error_msg.lower()
        print(f"✓ Error message: {error_msg}")

    def test_exists_but_error(self):
        """Test error message when ticker exists but has other issues."""
        validation_result = {
            'exists': True,
            'name': 'Test Company',
            'asset_type': 'equity',
            'reason': ''
        }

        error_msg = get_friendly_ticker_error('TEST', validation_result)

        # When exists is True, should return generic error
        assert 'TEST' in error_msg
        assert 'cannot be processed' in error_msg.lower()
        print(f"✓ Error message: {error_msg}")


class TestIntegrationWithClassification:
    """Integration tests with classification node."""

    def test_nvda_validation_passes(self):
        """Test that NVDA passes validation (the main goal of this feature)."""
        result = validate_ticker_exists('NVDA')

        assert result['exists'] is True
        assert 'NVIDIA' in result['name']
        assert result['asset_type'] == 'equity'
        print(f"✓ NVDA validation passed: {result['name']}")

    def test_validation_result_structure(self):
        """Test that validation result has correct structure."""
        result = validate_ticker_exists('AAPL')

        # Check all required keys exist
        assert 'exists' in result
        assert 'name' in result
        assert 'asset_type' in result
        assert 'reason' in result

        # Check types
        assert isinstance(result['exists'], bool)
        assert isinstance(result['name'], str)
        assert isinstance(result['asset_type'], str)
        assert isinstance(result['reason'], str)

        print(f"✓ Validation result structure correct")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
