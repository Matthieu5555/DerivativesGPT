"""Tests for parallel task execution with mocked asyncio."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from derivatives_gpt_core.graph_nodes.execute_parallel_tasks import (
    execute_task,
    execute_parallel_group,
    execute_plan
)
from derivatives_gpt_core.graph_state_schema import OptionPricingState


@pytest.fixture
def mock_state():
    """Create a mock state for testing."""
    return OptionPricingState(
        messages=[],
        ticker="AAPL",
        spot_price=150.0,
        strike_price=155.0,
        time_to_expiry_days=30,
        volatility=0.25,
        risk_free_rate=0.045,
        option_type="call",
        strategy_type="single"
    )


@pytest.fixture
def market_data_task():
    """Create a market data task."""
    return {
        "id": "task_1",
        "type": "market_data",
        "params": {"ticker": "AAPL"}
    }


@pytest.fixture
def volatility_task():
    """Create a volatility task."""
    return {
        "id": "task_2",
        "type": "volatility",
        "params": {"ticker": "AAPL"}
    }


@pytest.fixture
def risk_free_rate_task():
    """Create a risk-free rate task."""
    return {
        "id": "task_3",
        "type": "risk_free_rate",
        "params": {}
    }


@pytest.fixture
def pricing_task():
    """Create a pricing task."""
    return {
        "id": "task_4",
        "type": "pricing",
        "params": {
            "option_type": "call",
            "strike": 155.0
        }
    }


@pytest.mark.asyncio
async def test_execute_task_market_data(market_data_task, mock_state):
    """Test market data task execution."""
    with patch("derivatives_gpt_core.graph_nodes.execute_parallel_tasks.yf.Ticker") as mock_ticker:
        # Mock Yahoo Finance response
        mock_hist = Mock()
        mock_hist.empty = False
        mock_hist['Close'].iloc = [150.5]
        mock_ticker.return_value.history.return_value = mock_hist

        result = await execute_task(market_data_task, mock_state)

        assert result["id"] == "task_1"
        assert "output" in result
        assert result["output"]["spot_price"] == 150.5
        assert "error" not in result


@pytest.mark.asyncio
async def test_execute_task_market_data_failure(market_data_task, mock_state):
    """Test market data task with no data available."""
    with patch("derivatives_gpt_core.graph_nodes.execute_parallel_tasks.yf.Ticker") as mock_ticker:
        # Mock empty history
        mock_hist = Mock()
        mock_hist.empty = True
        mock_ticker.return_value.history.return_value = mock_hist

        result = await execute_task(market_data_task, mock_state)

        assert result["id"] == "task_1"
        assert "error" in result
        assert "No market data" in result["error"]


@pytest.mark.asyncio
async def test_execute_task_volatility(volatility_task, mock_state):
    """Test volatility task execution."""
    with patch("derivatives_gpt_core.graph_nodes.execute_parallel_tasks.estimate_annualized_volatility") as mock_vol:
        mock_vol.invoke.return_value = "Estimated volatility: 25.3%"

        result = await execute_task(volatility_task, mock_state)

        assert result["id"] == "task_2"
        assert "output" in result
        assert "volatility" in result["output"]
        assert result["output"]["volatility"] == pytest.approx(0.253, rel=0.01)


@pytest.mark.asyncio
async def test_execute_task_volatility_fallback(volatility_task, mock_state):
    """Test volatility task with unparseable response."""
    with patch("derivatives_gpt_core.graph_nodes.execute_parallel_tasks.estimate_annualized_volatility") as mock_vol:
        mock_vol.invoke.return_value = "Unable to calculate volatility"

        result = await execute_task(volatility_task, mock_state)

        assert result["id"] == "task_2"
        assert "output" in result
        assert "volatility" in result["output"]
        # Should use fallback value
        assert result["output"]["volatility"] == 0.3


@pytest.mark.asyncio
async def test_execute_task_risk_free_rate(risk_free_rate_task, mock_state):
    """Test risk-free rate task execution."""
    with patch("derivatives_gpt_core.graph_nodes.execute_parallel_tasks.estimate_risk_free_rate") as mock_rate:
        mock_rate.invoke.return_value = "Risk-free rate: 4.5%"

        result = await execute_task(risk_free_rate_task, mock_state)

        assert result["id"] == "task_3"
        assert "output" in result
        assert "risk_free_rate" in result["output"]
        assert result["output"]["risk_free_rate"] == pytest.approx(0.045, rel=0.01)


@pytest.mark.asyncio
async def test_execute_task_pricing(pricing_task, mock_state):
    """Test pricing task execution."""
    with patch("derivatives_gpt_core.graph_nodes.execute_parallel_tasks.calculate_black_scholes_price") as mock_bs:
        mock_bs.return_value = 5.75

        result = await execute_task(pricing_task, mock_state)

        assert result["id"] == "task_4"
        assert "output" in result
        assert result["output"]["price"] == 5.75
        assert result["output"]["option_type"] == "call"
        assert result["output"]["strike"] == 155.0


@pytest.mark.asyncio
async def test_execute_task_pricing_missing_params(mock_state):
    """Test pricing task with missing parameters."""
    task = {
        "id": "task_4",
        "type": "pricing",
        "params": {"option_type": "call"}
    }
    # Clear required params
    mock_state.spot_price = None

    result = await execute_task(task, mock_state)

    assert result["id"] == "task_4"
    assert "error" in result
    assert "Missing required parameters" in result["error"]


@pytest.mark.asyncio
async def test_execute_task_unknown_type(mock_state):
    """Test task with unknown type."""
    task = {"id": "task_x", "type": "unknown_type", "params": {}}

    result = await execute_task(task, mock_state)

    assert result["id"] == "task_x"
    assert "error" in result
    assert "Unknown task type" in result["error"]


@pytest.mark.asyncio
async def test_execute_parallel_group(market_data_task, volatility_task, mock_state):
    """Test parallel execution of multiple tasks."""
    with patch("derivatives_gpt_core.graph_nodes.execute_parallel_tasks.yf.Ticker") as mock_ticker, \
         patch("derivatives_gpt_core.graph_nodes.execute_parallel_tasks.estimate_annualized_volatility") as mock_vol:

        # Mock market data
        mock_hist = Mock()
        mock_hist.empty = False
        mock_hist['Close'].iloc = [150.5]
        mock_ticker.return_value.history.return_value = mock_hist

        # Mock volatility
        mock_vol.invoke.return_value = "Estimated volatility: 25.3%"

        tasks = [market_data_task, volatility_task]
        results = await execute_parallel_group(tasks, mock_state)

        assert len(results) == 2
        assert results[0]["id"] == "task_1"
        assert results[1]["id"] == "task_2"
        assert "output" in results[0]
        assert "output" in results[1]


def test_execute_plan_no_plan(mock_state):
    """Test execute_plan with no execution plan."""
    mock_state.execution_plan = None

    result = execute_plan(mock_state)

    assert "execution_results" in result
    assert result["execution_results"] == {}


def test_execute_plan_single_option(mock_state):
    """Test execute_plan for single option pricing."""
    mock_state.execution_plan = {
        "tasks": [
            {"id": "task_1", "type": "market_data", "params": {"ticker": "AAPL"}},
            {"id": "task_2", "type": "pricing", "params": {"option_type": "call", "strike": 155.0}}
        ],
        "parallel_groups": [["task_1"], ["task_2"]]
    }

    with patch("derivatives_gpt_core.graph_nodes.execute_parallel_tasks.asyncio.run") as mock_run, \
         patch("derivatives_gpt_core.graph_nodes.execute_parallel_tasks.yf.Ticker") as mock_ticker, \
         patch("derivatives_gpt_core.graph_nodes.execute_parallel_tasks.calculate_black_scholes_price") as mock_bs:

        # Mock market data result
        mock_hist = Mock()
        mock_hist.empty = False
        mock_hist['Close'].iloc = [150.5]
        mock_ticker.return_value.history.return_value = mock_hist

        # Mock pricing result
        mock_bs.return_value = 5.75

        # Mock asyncio.run to return results sequentially
        def run_side_effect(coro):
            import asyncio
            return asyncio.get_event_loop().run_until_complete(coro)

        mock_run.side_effect = run_side_effect

        result = execute_plan(mock_state)

        assert "execution_results" in result
        assert "spot_price" in result
        assert "option_price" in result
        assert result["option_price"] == 5.75


def test_execute_plan_multi_leg(mock_state):
    """Test execute_plan for multi-leg strategy."""
    mock_state.strategy_type = "straddle"
    mock_state.multi_leg = True
    mock_state.execution_plan = {
        "tasks": [
            {"id": "task_1", "type": "market_data", "params": {"ticker": "AAPL"}},
            {"id": "task_2", "type": "pricing", "params": {"option_type": "call", "strike": 150.0}},
            {"id": "task_3", "type": "pricing", "params": {"option_type": "put", "strike": 150.0}}
        ],
        "parallel_groups": [["task_1"], ["task_2", "task_3"]]
    }

    with patch("derivatives_gpt_core.graph_nodes.execute_parallel_tasks.asyncio.run") as mock_run, \
         patch("derivatives_gpt_core.graph_nodes.execute_parallel_tasks.yf.Ticker") as mock_ticker, \
         patch("derivatives_gpt_core.graph_nodes.execute_parallel_tasks.calculate_black_scholes_price") as mock_bs:

        # Mock market data
        mock_hist = Mock()
        mock_hist.empty = False
        mock_hist['Close'].iloc = [150.0]
        mock_ticker.return_value.history.return_value = mock_hist

        # Mock pricing - return different values for call and put
        mock_bs.side_effect = [6.50, 6.25]

        # Mock asyncio.run
        def run_side_effect(coro):
            import asyncio
            return asyncio.get_event_loop().run_until_complete(coro)

        mock_run.side_effect = run_side_effect

        result = execute_plan(mock_state)

        assert "execution_results" in result
        assert "spot_price" in result
        # Multi-leg should NOT have option_price in execute_plan result
        assert "option_price" not in result


def test_execute_plan_with_errors(mock_state):
    """Test execute_plan with task failures."""
    mock_state.execution_plan = {
        "tasks": [
            {"id": "task_1", "type": "market_data", "params": {"ticker": "INVALID"}}
        ],
        "parallel_groups": [["task_1"]]
    }

    with patch("derivatives_gpt_core.graph_nodes.execute_parallel_tasks.asyncio.run") as mock_run, \
         patch("derivatives_gpt_core.graph_nodes.execute_parallel_tasks.yf.Ticker") as mock_ticker:

        # Mock empty history (failure)
        mock_hist = Mock()
        mock_hist.empty = True
        mock_ticker.return_value.history.return_value = mock_hist

        def run_side_effect(coro):
            import asyncio
            return asyncio.get_event_loop().run_until_complete(coro)

        mock_run.side_effect = run_side_effect

        result = execute_plan(mock_state)

        assert "execution_results" in result
        # Task should fail, so results should be empty
        assert len(result["execution_results"]) == 0


@pytest.mark.asyncio
async def test_execute_task_atm_strike(mock_state):
    """Test pricing task with ATM strike specification."""
    task = {
        "id": "task_4",
        "type": "pricing",
        "params": {
            "option_type": "call",
            "strike": "ATM"
        }
    }
    mock_state.spot_price = 150.0

    with patch("derivatives_gpt_core.graph_nodes.execute_parallel_tasks.calculate_black_scholes_price") as mock_bs:
        mock_bs.return_value = 5.75

        result = await execute_task(task, mock_state)

        assert result["id"] == "task_4"
        assert "output" in result
        # Should use spot price as strike
        mock_bs.assert_called_once()
        assert mock_bs.call_args[1]["strike_price"] == 150.0
