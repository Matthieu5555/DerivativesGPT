"""
Workflow Explorer - Functional implementation.

Automatically extract and document LangGraph agent workflow structure using
pure functional programming approach.
"""

import ast
import json
from pathlib import Path
from typing import Dict, List, Any, Set, Optional, Tuple
import argparse


# ============================================================================
# AST PARSING UTILITIES
# ============================================================================

def parse_file(file_path: Path) -> ast.AST:
    """Parse Python file into AST."""
    with open(file_path, 'r') as f:
        return ast.parse(f.read())


def get_string_value(node: ast.AST) -> Optional[str]:
    """Extract string value from AST node."""
    if isinstance(node, ast.Constant):
        return str(node.value) if node.value is not None else None
    elif hasattr(ast, 'Str') and isinstance(node, ast.Str):
        return node.s
    return None


def get_name_value(node: ast.AST) -> Optional[str]:
    """Extract name/identifier from AST node."""
    return node.id if isinstance(node, ast.Name) else None


def is_end_constant(node: ast.AST) -> bool:
    """Check if node represents END constant."""
    if isinstance(node, ast.Name):
        return node.id == "END"
    elif isinstance(node, ast.Constant):
        return node.value in ("__end__", "END")
    elif hasattr(ast, 'Str') and isinstance(node, ast.Str):
        return node.s in ("__end__", "END")
    return False


def ast_to_text(node: ast.AST) -> str:
    """Convert AST node to readable text."""
    if isinstance(node, ast.Attribute):
        return f"{ast_to_text(node.value)}.{node.attr}"
    elif isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Constant):
        return repr(node.value)
    return "value"


def op_to_text(op: ast.AST) -> str:
    """Convert comparison operator to text."""
    mapping = {
        ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=",
        ast.Gt: ">", ast.GtE: ">=", ast.Is: "is", ast.IsNot: "is not",
        ast.In: "in", ast.NotIn: "not in"
    }
    return mapping.get(type(op), "?")


# ============================================================================
# GRAPH STRUCTURE EXTRACTION
# ============================================================================

def extract_node_calls(tree: ast.AST) -> Dict[str, str]:
    """
    Extract workflow.add_node() calls.

    Returns:
        dict: {node_name: function_name}
    """
    node_functions = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "add_node":
                if len(node.args) >= 2:
                    node_name = get_string_value(node.args[0])
                    func_name = get_name_value(node.args[1])
                    if node_name and func_name and node_name not in node_functions:
                        node_functions[node_name] = func_name

    return node_functions


def extract_entry_point(tree: ast.AST) -> Optional[str]:
    """Extract workflow.set_entry_point() call."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == "set_entry_point":
                if node.args:
                    return get_string_value(node.args[0])
    return None


def extract_edges(tree: ast.AST) -> Tuple[List[Dict], Set[str]]:
    """
    Extract workflow.add_edge() calls.

    Returns:
        tuple: (edges list, endpoints set)
    """
    edges = []
    endpoints = set()

    for stmt in ast.walk(tree):
        if not isinstance(stmt, ast.Call):
            continue

        if not isinstance(stmt.func, ast.Attribute):
            continue

        # Standard edges
        if stmt.func.attr == "add_edge" and len(stmt.args) >= 2:
            source = get_string_value(stmt.args[0])

            if is_end_constant(stmt.args[1]):
                if source:
                    endpoints.add(source)
            else:
                target = get_string_value(stmt.args[1])
                if source and target:
                    edge = {
                        "source": source,
                        "target": target,
                        "type": "standard",
                        "condition": None
                    }
                    if edge not in edges:
                        edges.append(edge)

    return edges, endpoints


def extract_condition_text(test_node: ast.AST, source: str) -> str:
    """Extract human-readable condition from AST test node."""
    if isinstance(test_node, ast.Compare):
        left = ast_to_text(test_node.left)
        ops = [op_to_text(op) for op in test_node.ops]
        comparators = [ast_to_text(comp) for comp in test_node.comparators]

        parts = [left]
        for op, comp in zip(ops, comparators):
            parts.extend([op, comp])
        return ' '.join(parts)

    elif isinstance(test_node, ast.BoolOp):
        op_text = " and " if isinstance(test_node.op, ast.And) else " or "
        values = [extract_condition_text(v, source) for v in test_node.values]
        return op_text.join(values)

    return "condition check"


def extract_routing_conditions(router_func_name: str, source_code: str) -> Dict[str, str]:
    """Extract routing conditions from router function."""
    tree = ast.parse(source_code)
    conditions = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == router_func_name:
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.If):
                    condition_text = extract_condition_text(stmt.test, source_code)

                    for substmt in ast.walk(stmt):
                        if isinstance(substmt, ast.Return):
                            target = get_string_value(substmt.value)
                            if target:
                                conditions[target] = condition_text
            break

    return conditions


def extract_edge_mapping(mapping_node: ast.AST) -> Dict[str, str]:
    """Extract edge mapping from dict literal."""
    mapping = {}

    if isinstance(mapping_node, ast.Dict):
        for key, value in zip(mapping_node.keys, mapping_node.values):
            key_str = get_string_value(key)
            value_str = get_string_value(value)
            if key_str and value_str:
                mapping[value_str] = key_str

    return mapping


def extract_conditional_edges(tree: ast.AST, source_code: str) -> Tuple[List[Dict], Set[str]]:
    """Extract workflow.add_conditional_edges() calls."""
    edges = []
    endpoints = set()

    for stmt in ast.walk(tree):
        if not isinstance(stmt, ast.Call):
            continue

        if isinstance(stmt.func, ast.Attribute) and stmt.func.attr == "add_conditional_edges":
            if len(stmt.args) >= 3:
                source = get_string_value(stmt.args[0])
                router_func = get_name_value(stmt.args[1])
                mapping = extract_edge_mapping(stmt.args[2])

                if source and mapping:
                    conditions = extract_routing_conditions(router_func, source_code) if router_func else {}

                    for target, condition_key in mapping.items():
                        if target in ("END", "__end__"):
                            endpoints.add(source)
                        else:
                            edge = {
                                "source": source,
                                "target": target,
                                "type": "conditional",
                                "condition": conditions.get(target, condition_key)
                            }
                            if edge not in edges:
                                edges.append(edge)

    return edges, endpoints


def parse_graph_definition(graph_file: Path) -> Tuple[Dict[str, str], Optional[str], List[Dict], Set[str]]:
    """
    Parse agent graph definition file.

    Returns:
        tuple: (node_functions, entrypoint, edges, endpoints)
    """
    with open(graph_file, 'r') as f:
        content = f.read()

    tree = ast.parse(content)

    # Find create_option_pricing_graph function
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "create_option_pricing_graph":
            node_functions = extract_node_calls(node)
            entrypoint = extract_entry_point(node)

            standard_edges, standard_endpoints = extract_edges(node)
            conditional_edges, conditional_endpoints = extract_conditional_edges(node, content)

            all_edges = standard_edges + conditional_edges
            all_endpoints = standard_endpoints | conditional_endpoints

            return node_functions, entrypoint, all_edges, all_endpoints

    return {}, None, [], set()


# ============================================================================
# NODE DETAILS EXTRACTION
# ============================================================================

def extract_inputs_from_function(func_node: ast.FunctionDef) -> List[str]:
    """Extract state fields read by function."""
    inputs = set()

    for node in ast.walk(func_node):
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "state":
                inputs.add(node.attr)

    return sorted(list(inputs))


def extract_outputs_from_function(func_node: ast.FunctionDef) -> List[str]:
    """Extract state fields written by function."""
    outputs = set()

    for node in ast.walk(func_node):
        if isinstance(node, ast.Return):
            if isinstance(node.value, ast.Dict):
                for key in node.value.keys:
                    if isinstance(key, (ast.Constant, ast.Str)):
                        key_value = key.value if isinstance(key, ast.Constant) else key.s
                        outputs.add(key_value)
            elif isinstance(node.value, ast.Call):
                if isinstance(node.value.func, ast.Name) and node.value.func.id == "dict":
                    for keyword in node.value.keywords:
                        outputs.add(keyword.arg)

    return sorted(list(outputs))


def find_node_file(func_name: str, nodes_dir: Path) -> Optional[Path]:
    """Find file containing node function."""
    for py_file in nodes_dir.glob("*.py"):
        if py_file.name == "__init__.py":
            continue

        with open(py_file, 'r') as f:
            content = f.read()
            if f"def {func_name}" in content or f"async def {func_name}" in content:
                return py_file

    return None


def extract_node_details_from_file(file_path: Path, func_name: str, project_root: Path) -> Dict[str, Any]:
    """Extract node details from implementation file."""
    tree = parse_file(file_path)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            docstring = ast.get_docstring(node) or ""
            description = docstring.split('\n')[0].strip() if docstring else f"Node: {func_name}"

            return {
                "description": description,
                "inputs": extract_inputs_from_function(node),
                "outputs": extract_outputs_from_function(node)
            }

    return {"description": f"Node: {func_name}", "inputs": [], "outputs": []}


def extract_all_node_details(
    node_functions: Dict[str, str],
    nodes_dir: Path,
    graph_file: Path,
    project_root: Path
) -> List[Dict[str, Any]]:
    """Extract details for all nodes."""
    nodes = []
    seen = set()

    for node_name, func_name in node_functions.items():
        if node_name in seen:
            continue
        seen.add(node_name)

        # Find implementation file
        node_file = find_node_file(func_name, nodes_dir)

        if node_file:
            details = extract_node_details_from_file(node_file, func_name, project_root)
        else:
            # Try graph definition file (inline handlers)
            details = extract_node_details_from_file(graph_file, func_name, project_root)

        nodes.append({
            "name": node_name,
            "description": details.get("description", f"Node: {node_name}"),
            "inputs": details.get("inputs", []),
            "outputs": details.get("outputs", [])
        })

    return nodes


# ============================================================================
# TOOL EXTRACTION
# ============================================================================

def get_type_annotation(annotation: ast.AST) -> str:
    """Convert type annotation AST to string."""
    if isinstance(annotation, ast.Name):
        return annotation.id
    elif isinstance(annotation, ast.Constant):
        return str(annotation.value)
    elif isinstance(annotation, ast.Subscript):
        value = get_type_annotation(annotation.value)
        slice_val = get_type_annotation(annotation.slice)
        return f"{value}[{slice_val}]"
    elif isinstance(annotation, ast.Tuple):
        elements = [get_type_annotation(e) for e in annotation.elts]
        return f"({', '.join(elements)})"
    elif isinstance(annotation, ast.BinOp):
        left = get_type_annotation(annotation.left)
        right = get_type_annotation(annotation.right)
        return f"{left} | {right}"
    return "Any"


def extract_docstring_section(docstring: str, section_name: str) -> str:
    """Extract specific section from docstring."""
    if not docstring:
        return ""

    lines = docstring.split('\n')
    in_section = False
    section_lines = []

    for line in lines:
        stripped = line.strip()

        if stripped.startswith(section_name + ":") or stripped == section_name:
            in_section = True
            continue

        if in_section and stripped and stripped[0].isupper() and stripped.endswith(':'):
            break

        if in_section and stripped:
            section_lines.append(stripped)

    return ' '.join(section_lines)


def is_tool_function(func_node: ast.FunctionDef) -> bool:
    """Check if function is decorated with @tool."""
    for decorator in func_node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "tool":
            return True
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name) and decorator.func.id == "tool":
                return True
    return False


def extract_tool_from_function(func_node: ast.FunctionDef, file_path: Path, project_root: Path) -> Dict[str, Any]:
    """Extract tool details from function."""
    docstring = ast.get_docstring(func_node) or ""
    description = docstring.split('\n')[0].strip() if docstring else f"Tool: {func_node.name}"

    parameters = [
        {
            "name": arg.arg,
            "type": get_type_annotation(arg.annotation) if arg.annotation else "Any"
        }
        for arg in func_node.args.args
    ]

    return_type = get_type_annotation(func_node.returns) if func_node.returns else "Any"
    when_to_use = extract_docstring_section(docstring, "WHEN TO USE")

    return {
        "name": func_node.name,
        "description": description,
        "file": str(file_path.relative_to(project_root)),
        "parameters": parameters,
        "returns": return_type,
        "when_to_use": when_to_use
    }


def extract_tools(tools_dir: Path, project_root: Path) -> List[Dict[str, Any]]:
    """Extract all LangChain tools from tools directory."""
    if not tools_dir.exists():
        return []

    tools = []

    for tool_file in tools_dir.glob("*.py"):
        if tool_file.name == "__init__.py":
            continue

        try:
            tree = parse_file(tool_file)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if is_tool_function(node):
                    tool = extract_tool_from_function(node, tool_file, project_root)
                    tools.append(tool)

    return tools


# ============================================================================
# MAIN WORKFLOW EXTRACTION
# ============================================================================

def extract_workflow(project_root: Path) -> Dict[str, Any]:
    """
    Extract complete workflow structure.

    Pure functional implementation - no classes, no mutable state.
    """
    print("[INFO] Analyzing workflow structure...")

    # Setup paths
    graph_file = project_root / "derivatives_gpt_core" / "agent_graph_definition.py"
    nodes_dir = project_root / "derivatives_gpt_core" / "graph_nodes"
    tools_dir = project_root / "derivatives_gpt_core" / "langchain_tools"

    # Extract graph structure
    print("[INFO] Parsing graph definition...")
    node_functions, entrypoint, edges, endpoints = parse_graph_definition(graph_file)

    # Extract node details
    print("[INFO] Extracting node details...")
    nodes = extract_all_node_details(node_functions, nodes_dir, graph_file, project_root)

    # Extract tools
    print("[INFO] Extracting tool details...")
    tools = extract_tools(tools_dir, project_root)

    print(f"[SUCCESS] Extracted {len(nodes)} nodes, {len(edges)} edges, {len(tools)} tools")

    return {
        "graph": {
            "entrypoint": entrypoint,
            "endpoints": sorted(list(endpoints)),
            "nodes": nodes,
            "edges": edges,
            "tools": tools
        }
    }


def save_workflow(workflow: Dict[str, Any], output_path: Path, pretty: bool = True):
    """Save workflow to JSON file."""
    indent = 2 if pretty else None
    with open(output_path, 'w') as f:
        json.dump(workflow, f, indent=indent)
    print(f"[SUCCESS] Saved to {output_path}")


def print_summary(workflow: Dict[str, Any]):
    """Print workflow summary."""
    graph = workflow["graph"]

    print("\n" + "=" * 60)
    print("WORKFLOW SUMMARY")
    print("=" * 60)
    print(f"\nEntry Point: {graph['entrypoint']}")
    print(f"Exit Points: {', '.join(graph['endpoints'])}")
    print(f"Total Nodes: {len(graph['nodes'])}")
    print(f"Total Edges: {len(graph['edges'])}")
    print(f"Total Tools: {len(graph['tools'])}")
    print("\n" + "=" * 60)


# ============================================================================
# CLI
# ============================================================================

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Extract LangGraph workflow structure")
    parser.add_argument("--output", "-o", default="workflow_structure.json", help="Output file")
    parser.add_argument("--summary", "-s", action="store_true", help="Print summary")
    parser.add_argument("--pretty", "-p", action="store_true", default=True, help="Pretty JSON")

    args = parser.parse_args()

    # Project root is parent of dev_tools/
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Extract workflow
    workflow = extract_workflow(project_root)

    # Save
    output_path = project_root / args.output
    save_workflow(workflow, output_path, args.pretty)

    # Print summary
    if args.summary:
        print_summary(workflow)


if __name__ == "__main__":
    main()
