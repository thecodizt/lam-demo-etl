import networkx as nx
import plotly.graph_objects as go
import random
from typing import Dict, List, Any, Tuple
import numpy as np
from itertools import combinations
import matplotlib.pyplot as plt
from collections import defaultdict


def find_matching_strings(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> List[str]:
    """Find matching string values between two dictionaries"""
    matches = []
    for k1, v1 in dict1.items():
        for k2, v2 in dict2.items():
            if isinstance(v1, str) and isinstance(v2, str) and v1.lower() == v2.lower():
                matches.append(f"{k1}={v1}")
    return matches


def create_graph(data: Dict[str, List[Dict[str, Any]]]) -> nx.Graph:
    """
    Create a networkx graph from the data where:
    - Nodes are items from any type
    - Edges connect items that share matching string values
    Returns the graph object for further processing
    """
    G = nx.Graph()

    # Add nodes for each item in each type
    for type_name, items in data.items():
        for item in items:
            # Create a unique node ID using type and a key value if available
            node_id = f"{type_name}_{item.get('id', item.get('Part', item.get('Name', str(hash(str(item))))))}"
            G.add_node(node_id, type=type_name, **item)

    # Add edges between nodes of the same type
    for type_name, items in data.items():
        for item1, item2 in combinations(items, 2):
            matches = find_matching_strings(item1, item2)
            if matches:
                node1 = f"{type_name}_{item1.get('id', item1.get('Part', item1.get('Name', str(hash(str(item1))))))}"
                node2 = f"{type_name}_{item2.get('id', item2.get('Part', item2.get('Name', str(hash(str(item2))))))}"
                G.add_edge(
                    node1,
                    node2,
                    relationship=f"same_{type_name}_matches",
                    matches=matches,
                )

    # Add edges between nodes of different types
    for type1, items1 in data.items():
        for type2, items2 in data.items():
            if type1 >= type2:  # Skip if we've already done this pair
                continue
            for item1 in items1:
                for item2 in items2:
                    matches = find_matching_strings(item1, item2)
                    if matches:
                        node1 = f"{type1}_{item1.get('id', item1.get('Part', item1.get('Name', str(hash(str(item1))))))}"
                        node2 = f"{type2}_{item2.get('id', item2.get('Part', item2.get('Name', str(hash(str(item2))))))}"
                        G.add_edge(
                            node1,
                            node2,
                            relationship=f"{type1}_{type2}_match",
                            matches=matches,
                        )

    return G


def get_graph_stats(G: nx.Graph) -> Dict[str, Any]:
    """
    Get statistics about the graph including:
    - Total nodes and edges
    - Nodes per type
    - Edges per relationship type
    """
    stats = {
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "nodes_by_type": defaultdict(int),
        "edges_by_type": defaultdict(int),
        "avg_degree": (
            2 * G.number_of_edges() / G.number_of_nodes()
            if G.number_of_nodes() > 0
            else 0
        ),
    }

    # Count nodes by type
    for node, attrs in G.nodes(data=True):
        stats["nodes_by_type"][attrs["type"]] += 1

    # Count edges by relationship
    for _, _, attrs in G.edges(data=True):
        stats["edges_by_type"][attrs["relationship"]] += 1

    # Convert defaultdicts to regular dicts
    stats["nodes_by_type"] = dict(stats["nodes_by_type"])
    stats["edges_by_type"] = dict(stats["edges_by_type"])

    return stats


def get_random_subgraph(G: nx.Graph, n: int) -> Tuple[nx.Graph, List[str]]:
    """
    Get a random subgraph with n nodes and their neighbors
    """
    if n > len(G.nodes):
        n = len(G.nodes)

    # Select random seed nodes
    seed_nodes = random.sample(list(G.nodes), n)

    # Get the subgraph including neighbors
    nodes_to_include = set(seed_nodes)
    for node in seed_nodes:
        nodes_to_include.update(G.neighbors(node))

    return G.subgraph(nodes_to_include), seed_nodes


def visualize_graph(G: nx.Graph, selected_nodes: List[str] = None) -> go.Figure:
    """
    Create an interactive plotly visualization of the graph
    G: The full graph
    selected_nodes: List of nodes to visualize (will include their direct connections)
    """
    if selected_nodes:
        # Get the subgraph of selected nodes and their neighbors
        nodes_to_include = set(selected_nodes)
        for node in selected_nodes:
            nodes_to_include.update(G.neighbors(node))
        G = G.subgraph(nodes_to_include)

    # Create layout
    pos = nx.spring_layout(G, k=1, iterations=50)

    # Create edge trace
    edge_x = []
    edge_y = []
    edge_text = []

    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

        # Add edge information
        edge_data = G.edges[edge]
        edge_text.extend(
            [
                f"Relationship: {edge_data['relationship']}<br>"
                f"Matches: {', '.join(edge_data.get('matches', []))}",
                "",  # Empty text for the second point
                "",  # Empty text for the None point
            ]
        )

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=1, color="#888"),
        hoverinfo="text",
        text=edge_text,
        mode="lines",
        name="Connections",
        showlegend=False,
    )

    # Create node traces by type
    node_traces = []

    # Get unique types and assign colors
    node_types = sorted(set(nx.get_node_attributes(G, "type").values()))

    # Define a custom color palette with vibrant, distinct colors
    color_palette = [
        "#4285F4",  # Google Blue
        "#34A853",  # Google Green
        "#FBBC05",  # Google Yellow
        "#EA4335",  # Google Red
        "#9C27B0",  # Deep Purple
        "#00ACC1",  # Cyan
        "#FF6D00",  # Deep Orange
        "#43A047",  # Green
        "#1E88E5",  # Blue
        "#6D4C41",  # Brown
        "#757575",  # Gray
        "#546E7A",  # Blue Gray
    ]

    # If we need more colors than in our palette, use a gradient
    if len(node_types) > len(color_palette):
        colors = plt.cm.viridis(np.linspace(0, 1, len(node_types)))
        type_to_color = {
            t: f"rgb({int(c[0]*255)},{int(c[1]*255)},{int(c[2]*255)})"
            for t, c in zip(node_types, colors)
        }
    else:
        # Use our custom palette
        type_to_color = {
            t: c for t, c in zip(node_types, color_palette[: len(node_types)])
        }

    for node_type in node_types:
        type_nodes = [n for n in G.nodes() if G.nodes[n]["type"] == node_type]

        x = []
        y = []
        text = []
        marker_color = []

        for node in type_nodes:
            x.append(pos[node][0])
            y.append(pos[node][1])

            # Node info for hover text
            node_info = G.nodes[node]
            hover_text = [
                f"{k}: {v}<br>"
                for k, v in node_info.items()
                if k not in ["type"] and isinstance(v, (str, int, float))
            ]
            text.append("".join(hover_text))

            # Different colors for selected nodes
            if selected_nodes and node in selected_nodes:
                marker_color.append("#e31a1c")  # Bright red for selected nodes
            else:
                marker_color.append(type_to_color[node_type])

        # Create separate traces for selected and non-selected nodes
        if selected_nodes:
            selected_x = []
            selected_y = []
            selected_text = []
            non_selected_x = []
            non_selected_y = []
            non_selected_text = []

            for i, node in enumerate(type_nodes):
                if node in selected_nodes:
                    selected_x.append(x[i])
                    selected_y.append(y[i])
                    selected_text.append(text[i])
                else:
                    non_selected_x.append(x[i])
                    non_selected_y.append(y[i])
                    non_selected_text.append(text[i])

            if selected_x:
                node_traces.append(
                    go.Scatter(
                        x=selected_x,
                        y=selected_y,
                        mode="markers",
                        hoverinfo="text",
                        text=selected_text,
                        name=f"Selected {node_type.replace('_', ' ').title()}",
                        marker=dict(
                            color="#e31a1c",  # Bright red
                            size=25,
                            line=dict(width=2, color="#fff"),
                            symbol="circle",
                        ),
                    )
                )

            if non_selected_x:
                node_traces.append(
                    go.Scatter(
                        x=non_selected_x,
                        y=non_selected_y,
                        mode="markers",
                        hoverinfo="text",
                        text=non_selected_text,
                        name=node_type.replace("_", " ").title(),
                        marker=dict(
                            color=type_to_color[node_type],
                            size=20,
                            line=dict(width=2, color="#fff"),
                            symbol="circle",
                        ),
                    )
                )
        else:
            node_traces.append(
                go.Scatter(
                    x=x,
                    y=y,
                    mode="markers",
                    hoverinfo="text",
                    text=text,
                    name=node_type.replace("_", " ").title(),
                    marker=dict(
                        color=marker_color,
                        size=20,
                        line=dict(width=2, color="#fff"),
                        symbol="circle",
                    ),
                )
            )

    # Create figure
    fig = go.Figure(
        data=[edge_trace] + node_traces,
        layout=go.Layout(
            title="Data Relationship Graph",
            showlegend=True,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01,
            ),
            paper_bgcolor="rgba(0,0,0,0)",
        ),
    )

    return fig


def visualize_random_items(
    data: Dict[str, List[Dict[str, Any]]], n: int = 5
) -> go.Figure:
    """
    Create and visualize a graph with n random items and their connections
    """
    # Create full graph
    G = create_graph(data)

    # Get random subgraph
    subG, seed_nodes = get_random_subgraph(G, n)

    # Create visualization
    return visualize_graph(subG, seed_nodes)
