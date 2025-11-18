"""
Generate Mermaid visualizations for all three agent graphs.
Saves PNG files to the graphs/ directory.
"""
import sys
from pathlib import Path
import asyncio

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from derivatives_gpt_core.core.graph.orchestrator_graph import build_orchestrator_graph
from derivatives_gpt_core.agents.pricing.graph import create_pricing_agent
from derivatives_gpt_core.agents.educational.graph import build_educational_agent_graph


async def generate_visualizations():
    """Generate and save all graph visualizations."""

    # Create output directory
    output_dir = project_root / "graphs"
    output_dir.mkdir(exist_ok=True)

    print("Building graphs...")

    # Build all three graphs
    orchestrator_graph = await build_orchestrator_graph()
    pricing_graph = create_pricing_agent()
    educational_graph = build_educational_agent_graph()

    graphs = [
        ("orchestrator_graph", orchestrator_graph, "Orchestrator"),
        ("pricing_agent_graph", pricing_graph, "Pricing Agent"),
        ("educational_agent_graph", educational_graph, "Educational Agent"),
    ]

    for base_name, graph, name in graphs:
        print(f"\nGenerating {name}...")

        # Save Mermaid text file (.mmd)
        mmd_path = output_dir / f"{base_name}.mmd"
        try:
            mermaid_text = graph.get_graph().draw_mermaid()
            with open(mmd_path, "w") as f:
                f.write(mermaid_text)
            print(f"✓ Saved Mermaid text: {mmd_path}")
        except Exception as e:
            print(f"✗ Failed to generate Mermaid text for {name}: {e}")

        # Also save as PNG if possible
        png_path = output_dir / f"{base_name}.png"
        try:
            img_data = graph.get_graph().draw_mermaid_png(background_color="white")
            with open(png_path, "wb") as f:
                f.write(img_data)
            print(f"✓ Saved PNG: {png_path}")
        except Exception as e:
            print(f"  (PNG generation skipped: mermaid.ink API unavailable)")

    print(f"\n{'='*60}")
    print(f"All visualizations saved to: {output_dir}")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(generate_visualizations())
