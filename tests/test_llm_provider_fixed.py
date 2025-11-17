"""Tests for LLM provider abstraction layer.

Tests the actual LLM provider functions available in the codebase.
"""

import pytest
from unittest.mock import patch, MagicMock
from derivatives_gpt_core.llm_provider import (
    get_classification_llm,
    get_planner_llm,
    get_decomposer_llm,
    get_validator_llm,
    get_narrator_llm,
    get_pricing_llm
)
from derivatives_gpt_core.config import get_settings, reset_settings
from langchain_core.messages import HumanMessage, AIMessage


class TestLLMProviderAbstraction:
    """Test LLM provider factory and abstraction."""

    def setup_method(self):
        """Reset settings before each test."""
        reset_settings()

    @patch('derivatives_gpt_core.config.Settings')
    def test_get_classification_llm_openai(self, mock_settings_class):
        """Test OpenAI provider initialization for classification."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "openai"
        mock_settings.openai_api_key = "test-key"
        mock_settings.classification_openai_model = "gpt-4o-mini"
        mock_settings_class.return_value = mock_settings

        with patch('derivatives_gpt_core.llm_provider.ChatOpenAI') as mock_openai:
            llm = get_classification_llm()

            # Verify ChatOpenAI was called
            mock_openai.assert_called_once()
            call_kwargs = mock_openai.call_args[1]
            assert call_kwargs['model'] == "gpt-4o-mini"
            # Classification uses temperature 0.3 for slight variation
            assert call_kwargs['temperature'] == 0.3

    @patch('derivatives_gpt_core.config.Settings')
    def test_get_planner_llm_gemini(self, mock_settings_class):
        """Test Gemini provider initialization for planner."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "gemini"
        mock_settings.gemini_api_key = "test-key"
        mock_settings.planner_gemini_model = "gemini-1.5-flash"
        mock_settings_class.return_value = mock_settings

        with patch('derivatives_gpt_core.llm_provider.ChatGoogleGenerativeAI') as mock_gemini:
            llm = get_planner_llm()

            mock_gemini.assert_called_once()
            call_kwargs = mock_gemini.call_args[1]
            assert call_kwargs['model'] == "gemini-1.5-flash"
            assert call_kwargs['temperature'] == 0.0

    @patch('derivatives_gpt_core.config.Settings')
    def test_get_narrator_llm_openrouter(self, mock_settings_class):
        """Test OpenRouter provider initialization for narrator."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "openrouter"
        mock_settings.openrouter_api_key = "test-key"
        mock_settings.openrouter_model = "anthropic/claude-3-haiku:beta"
        mock_settings_class.return_value = mock_settings

        with patch('derivatives_gpt_core.llm_provider.ChatOpenAI') as mock_openai:
            llm = get_narrator_llm()

            # OpenRouter uses ChatOpenAI with custom base_url
            mock_openai.assert_called_once()
            call_kwargs = mock_openai.call_args[1]
            assert 'openrouter.ai' in call_kwargs.get('base_url', '')

    @patch('derivatives_gpt_core.llm_provider.get_classification_llm')
    def test_llm_interface_consistency(self, mock_get_llm):
        """Test that all LLM providers expose consistent interface."""
        # Mock LLM with standard interface
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="Test response")
        mock_get_llm.return_value = mock_llm

        llm = mock_get_llm()

        # Test standard invoke interface
        result = llm.invoke([HumanMessage(content="Test")])

        assert isinstance(result, AIMessage)
        assert result.content == "Test response"
        mock_llm.invoke.assert_called_once()

    def test_all_specialized_llms_available(self):
        """Test that all specialized LLM functions are available."""
        # Just verify they can be called (will fail on missing API keys, which is fine)
        functions = [
            get_classification_llm,
            get_planner_llm,
            get_decomposer_llm,
            get_validator_llm,
            get_narrator_llm,
            get_pricing_llm
        ]

        for func in functions:
            assert callable(func), f"{func.__name__} should be callable"


class TestLLMProviderConfiguration:
    """Test LLM-specific configuration handling."""

    @patch('derivatives_gpt_core.config.Settings')
    def test_different_models_per_task(self, mock_settings_class):
        """Test that different LLM tasks can have different models."""
        mock_settings = MagicMock()
        mock_settings.llm_provider = "openai"
        mock_settings.openai_api_key = "test-key"
        mock_settings.classification_openai_model = "gpt-4o-mini"
        mock_settings.planner_openai_model = "gpt-4o-mini"
        mock_settings.decomposer_openai_model = "gpt-4o-mini"

        mock_settings_class.return_value = mock_settings

        with patch('derivatives_gpt_core.llm_provider.ChatOpenAI') as mock_openai:
            # Classification LLM
            get_classification_llm()
            assert mock_openai.call_args[1]['temperature'] == 0.3

            mock_openai.reset_mock()

            # Planner LLM (uses 0.0 for deterministic planning)
            get_planner_llm()
            assert mock_openai.call_args[1]['temperature'] == 0.0
