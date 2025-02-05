import networkx as nx
import pandas as pd
from typing import Dict, List, Any


def normalize_type(type_name: str) -> str:
    """Normalize type names by replacing spaces with underscores"""
    return type_name.replace(" ", "_")


def build_graph(data: Dict[str, List[Dict]], schema: Dict[str, List[Dict]]) -> nx.Graph:
    """
    Build a graph based on the schema where nodes are connected based on primary key matches
    """
    G = nx.Graph()

    # Normalize data keys
    normalized_data = {normalize_type(k): v for k, v in data.items()}

    # Create nodes and store primary key mapping
    node_pk_map = {}  # Format: {node_type: {pk_value: node_id}}

    # Create nodes based on schema
    for node_schema in schema["nodes"]:
        node_type = node_schema["type"]
        pk_field = node_schema["id"]

        if node_type in normalized_data:
            node_pk_map[node_type] = {}

            for node_data in normalized_data[node_type]:
                pk_value = str(node_data.get(pk_field))
                if pk_value:
                    # Create a unique node ID
                    node_id = f"{node_type}_{pk_value}"
                    # Add node with all its attributes
                    G.add_node(
                        node_id,
                        type=node_type,
                        pk_value=pk_value,
                        pk_field=pk_field,
                        **{k: v for k, v in node_data.items() if k != pk_field},
                    )
                    # Store mapping of primary key to node ID
                    node_pk_map[node_type][pk_value] = node_id

    for edge in schema["edges"]:
        # Get source and target types from the edge file name
        source_type, target_type = edge["source_node_type"], edge["target_node_type"]

        # Process each edge record
        for edge_data in normalized_data[edge["type"]]:
            # Get the first two columns as source and target
            columns = list(edge_data.keys())
            if len(columns) < 2:
                continue

            source_pk = str(edge_data[columns[0]])
            target_pk = str(edge_data[columns[1]])

            # Check if we have both nodes
            if (
                source_type in node_pk_map
                and target_type in node_pk_map
                and source_pk in node_pk_map[source_type]
                and target_pk in node_pk_map[target_type]
            ):

                source_id = node_pk_map[source_type][source_pk]
                target_id = node_pk_map[target_type][target_pk]

                # Add edge with all remaining columns as properties
                edge_props = {
                    k: v
                    for k, v in edge_data.items()
                    if k not in [columns[0], columns[1]]
                }
                edge_props["type"] = edge["type"]  # Add edge type property
                G.add_edge(source_id, target_id, **edge_props)

    return G


def get_node_features(G: nx.Graph, node_type: str) -> pd.DataFrame:
    """Get features for nodes of a specific type"""
    nodes = [
        (n, attr) for n, attr in G.nodes(data=True) if attr.get("type") == node_type
    ]
    if not nodes:
        return pd.DataFrame()

    return pd.DataFrame([attr for _, attr in nodes])


def get_edge_features(G: nx.Graph, edge_type: str) -> pd.DataFrame:
    """Get features for edges of a specific type"""
    edges = [
        (u, v, attr)
        for u, v, attr in G.edges(data=True)
        if attr.get("type") == edge_type
    ]
    if not edges:
        return pd.DataFrame()

    return pd.DataFrame([attr for _, _, attr in edges])


def export_features(G: nx.Graph, schema: Dict[str, List[Dict]], output_dir: str):
    """Export node and edge features to CSV files"""
    import os

    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Export node features
    for node_schema in schema["nodes"]:
        node_type = node_schema["type"]
        df = get_node_features(G, node_type)
        if not df.empty:
            df.to_csv(f"{output_dir}/{node_type}_features.csv", index=False)

    # Export edge features
    for edge_schema in schema["edges"]:
        edge_type = edge_schema["type"]
        df = get_edge_features(G, edge_type)
        if not df.empty:
            df.to_csv(f"{output_dir}/{edge_type}_features.csv", index=False)
