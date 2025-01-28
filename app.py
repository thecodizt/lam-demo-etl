import streamlit as st
import pandas as pd
import os
import extract
import transform
import load
import json
from datetime import datetime
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import random
import requests
import numpy as np
import logging

# Initialize logger
logger = logging.getLogger(__name__)


def display_graph_stats(G):
    """Display graph statistics"""
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Node Statistics")
        total_nodes = G.number_of_nodes()
        st.write(f"Total Nodes: {total_nodes}")

        # Count nodes by type
        node_types = {}
        for _, attr in G.nodes(data=True):
            node_type = attr.get("type", "Unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1

        # Create DataFrame for node type statistics
        node_stats = []
        for node_type, count in node_types.items():
            node_stats.append(
                {
                    "Node Type": node_type,
                    "Count": count,
                    "Percentage": f"{(count/total_nodes)*100:.1f}%",
                }
            )

        st.dataframe(pd.DataFrame(node_stats))

    with col2:
        st.subheader("Edge Statistics")
        total_edges = G.number_of_edges()
        st.write(f"Total Edges: {total_edges}")

        if total_edges > 0:
            # Count edges by type
            edge_types = {}
            for _, _, data in G.edges(data=True):
                edge_type = data.get("type", "Unknown")
                edge_types[edge_type] = edge_types.get(edge_type, 0) + 1

            # Create DataFrame for edge type statistics
            edge_stats = []
            for edge_type, count in edge_types.items():
                edge_stats.append(
                    {
                        "Edge Type": edge_type,
                        "Count": count,
                        "Percentage": f"{(count/total_edges)*100:.1f}%",
                    }
                )

            st.dataframe(pd.DataFrame(edge_stats))


def display_graph(G: nx.Graph, timestamp: str = "", max_nodes: int = 50):
    """Display graph using pyvis"""
    # Create a new graph for visualization
    vis_graph = nx.Graph()

    # Randomly sample nodes if there are too many
    nodes_to_show = list(G.nodes())
    if len(nodes_to_show) > max_nodes:
        nodes_to_show = random.sample(nodes_to_show, max_nodes)

    # Add selected nodes and their edges
    for node in nodes_to_show:
        # Add node with its attributes
        vis_graph.add_node(node, **G.nodes[node])

        # Add edges between selected nodes
        for neighbor in G.neighbors(node):
            if neighbor in nodes_to_show:
                vis_graph.add_edge(node, neighbor, **G.edges[node, neighbor])

    # Create and configure the pyvis network
    net = Network(notebook=True, height="500px", width="100%")

    # Add nodes with different colors based on type
    node_colors = {}
    for node, attrs in vis_graph.nodes(data=True):
        node_type = attrs.get("type", "default")
        if node_type not in node_colors:
            node_colors[node_type] = "#%06x" % random.randint(0, 0xFFFFFF)
        net.add_node(node, color=node_colors[node_type], title=str(attrs))

    # Add edges
    for source, target, attrs in vis_graph.edges(data=True):
        net.add_edge(source, target, title=str(attrs))

    # Generate HTML file
    html_file = f"cache/graph_{timestamp.replace(' ', '_')}.html"
    net.save_graph(html_file)

    # Read the generated HTML
    with open(html_file, "r") as f:
        source_code = f.read()
    components.html(source_code, height=500)


def clean_graph_data(G):
    """Clean graph data to ensure JSON compatibility"""
    # Clean node attributes
    for node in G.nodes():
        attrs = G.nodes[node]
        for key, value in list(attrs.items()):
            if pd.isna(value) or (
                isinstance(value, float) and (np.isnan(value) or np.isinf(value))
            ):
                attrs[key] = None

    # Clean edge attributes
    for u, v in G.edges():
        attrs = G.edges[u, v]
        for key, value in list(attrs.items()):
            if pd.isna(value) or (
                isinstance(value, float) and (np.isnan(value) or np.isinf(value))
            ):
                attrs[key] = None

    return G


def main():
    st.title("Graph ETL Pipeline")

    # Create cache directory if it doesn't exist
    if not os.path.exists("cache"):
        os.makedirs("cache")
    if not os.path.exists("cache/uploads"):
        os.makedirs("cache/uploads")

    # Section 1: Upload Data
    st.header("1. Upload Data")
    schema_file = st.file_uploader("Upload Schema (JSON)", type=["json"])
    data_files = st.file_uploader(
        "Upload Data (ZIP)", type=["zip"], accept_multiple_files=True
    )

    if not schema_file or not data_files:
        st.warning("Please upload both schema and data files to proceed")
        return

    # Save schema
    schema = json.load(schema_file)

    # Save data files
    data_to_process = []
    for data_file in data_files:
        try:
            timestamp = int(os.path.splitext(data_file.name)[0])
            timestamp_dir = os.path.join("cache/uploads", str(timestamp))
            if not os.path.exists(timestamp_dir):
                os.makedirs(timestamp_dir)
            filepath = os.path.join(timestamp_dir, data_file.name)
            with open(filepath, "wb") as f:
                f.write(data_file.getvalue())
            data_to_process.append(filepath)
        except ValueError:
            st.error(
                f"Invalid filename format for {data_file.name}. Expected timestamp."
            )
            return

    # Section 2: Extract
    st.header("2. Extract")
    extracted_data = {}

    for data_file in data_to_process:
        timestamp = os.path.splitext(os.path.basename(data_file))[0]
        display_time = datetime.fromtimestamp(int(timestamp)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        with st.expander(f"Data at {display_time}"):
            try:
                data = extract.read_zip(data_file)
                extracted_data[timestamp] = data
                st.json(json.loads(json.dumps(data, cls=load.NaNEncoder)))
            except Exception as e:
                st.error(f"Error extracting data from {data_file}: {str(e)}")
                continue

    # Section 3: Transform
    st.header("3. Transform")

    # Sort timestamps to ensure ordered processing
    all_timestamps = sorted(extracted_data.keys())
    debug_info = st.empty()
    debug_info.info(
        f"Found {len(all_timestamps)} timestamps to process: {all_timestamps}"
    )

    # Process all graphs first
    graphs = {}
    for timestamp in all_timestamps:
        try:
            # Build graph
            G = transform.build_graph(extracted_data[timestamp], schema)
            graphs[timestamp] = G
            logger.info(
                f"Built graph for timestamp {timestamp}: Nodes={len(G.nodes)}, Edges={len(G.edges)}"
            )
        except Exception as e:
            st.error(f"Error building graph for timestamp {timestamp}: {str(e)}")
            continue

    # Visualization controls for display only
    st.subheader("Visualization Controls")
    col1, col2 = st.columns(2)
    with col1:
        selected_timestamp = st.selectbox(
            "Select timestamp to visualize",
            options=all_timestamps,
            format_func=lambda x: datetime.fromtimestamp(int(x)).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        )
    with col2:
        max_nodes = st.slider(
            "Maximum nodes to display", min_value=5, max_value=100, value=50
        )

    # Display only the selected timestamp
    if selected_timestamp:
        display_time = datetime.fromtimestamp(int(selected_timestamp)).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        st.subheader(f"Graph at {display_time}")

        G = graphs[selected_timestamp]
        # Display statistics and graph
        display_graph_stats(G)
        display_graph(G, timestamp=display_time, max_nodes=max_nodes)

    # Section 4: Load
    st.header("4. Load")

    col1, col2 = st.columns(2)
    with col1:
        version = st.text_input("Version", value="v1")
    with col2:
        batch_size = st.number_input(
            "Batch Size", min_value=100, max_value=10000, value=1000, step=100
        )

    if st.button("Upload to Server"):
        if not graphs:
            st.error("No graphs to upload. Please process some data first.")
            return

        # Initialize progress container
        progress_container = st.empty()
        overall_progress = st.progress(0.0)
        status_text = st.empty()

        # Check server health first
        server = load.GraphServer()
        if not server.health_check():
            st.error("Server is not healthy. Please check server status and try again.")
            return

        try:
            # Sort timestamps to ensure ordered processing
            timestamps = sorted(graphs.keys())
            total_graphs = len(timestamps)
            logger.info(
                f"Found {total_graphs} graphs to process with timestamps: {timestamps}"
            )

            debug_container = st.empty()
            debug_container.info(
                f"Processing {total_graphs} graphs with timestamps: {timestamps}"
            )

            for idx, timestamp in enumerate(timestamps):
                G = graphs[timestamp]
                display_time = datetime.fromtimestamp(int(timestamp)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                logger.info(f"Processing graph {idx + 1}/{total_graphs}")
                logger.info(f"Timestamp: {timestamp} ({display_time})")
                logger.info(f"Graph info: Nodes={len(G.nodes)}, Edges={len(G.edges)}")

                status_text.write(
                    f"Processing graph {idx + 1}/{total_graphs} ({display_time})..."
                )

                # Convert graph to JSON
                graph_data = nx.node_link_data(G)

                # Prepare data for upload
                upload_data = {
                    "timestamp": int(timestamp),  # Ensure timestamp is an integer
                    "graph": graph_data,
                }

                # Upload to server - first timestamp uses bulk_create, others use bulk_update
                is_first_timestamp = idx == 0
                logger.info(f"Uploading with is_first_timestamp={is_first_timestamp}")

                response = load.upload_to_server(
                    upload_data,
                    version=version,
                    batch_size=batch_size,
                    is_first_timestamp=is_first_timestamp,
                )

                if response.get("success"):
                    action = "Created" if is_first_timestamp else "Updated"
                    message = (
                        f"{action} graph for {display_time}: {response.get('message')}"
                    )
                    st.success(message)
                    logger.info(message)
                else:
                    error = f"Failed to upload graph for {display_time}: {response.get('error')}"
                    st.error(error)
                    logger.error(error)

                # Update overall progress
                overall_progress.progress((idx + 1) / total_graphs)

        except Exception as e:
            error = f"Error uploading to server: {str(e)}"
            st.error(error)
            logger.error(error, exc_info=True)
        finally:
            # Clean up progress displays
            progress_container.empty()
            overall_progress.empty()
            status_text.empty()
            debug_container.empty()


if __name__ == "__main__":
    main()
