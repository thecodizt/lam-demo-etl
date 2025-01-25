import streamlit as st
import os
import json
import random
import pandas as pd
import numpy as np

import extract
import transform
import load

st.set_page_config(
    page_title="LAM - ETL",
    page_icon=":chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("LAM - ETL")


# Upload XLSX or ZIP File
def input():
    st.header("Upload Data")
    file = st.file_uploader(
        "Upload XLSX, ZIP, or JSON File", type=["xlsx", "zip", "json"]
    )

    data = None
    file_path = None

    # save file to cache dir
    if file:
        if not os.path.exists("cache"):
            os.makedirs("cache")
        with open(os.path.join("cache", file.name), "wb") as f:
            f.write(file.getbuffer())
        file_path = os.path.join("cache", file.name)
        st.success(f"File {file.name} uploaded successfully to {file_path}.")

    return file_path


class NaNEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle NaN, Infinity, and -Infinity values"""

    def _is_nan(self, obj):
        """Helper method to check for all possible NaN representations"""
        import numpy as np
        import pandas as pd

        if obj is None:
            return True
        if isinstance(obj, (float, np.floating)):
            return np.isnan(obj)
        if pd.isna(obj):
            return True
        if isinstance(obj, str) and obj.lower() == "nan":
            return True
        return False

    def default(self, obj):
        """Handle non-basic Python types"""
        import numpy as np

        if self._is_nan(obj):
            return None

        if isinstance(obj, (np.floating, float)):
            if np.isinf(obj):
                return "Infinity" if obj > 0 else "-Infinity"
            return float(obj)

        if isinstance(obj, (np.integer, np.bool_)):
            return int(obj)

        if isinstance(obj, np.ndarray):
            return obj.tolist()

        return super().default(obj)

    def encode(self, obj):
        """Override encode to handle NaN values in basic types"""
        if isinstance(obj, (dict, list)):
            return super().encode(self._handle_nan_in_container(obj))
        if self._is_nan(obj):
            return "null"
        return super().encode(obj)

    def _handle_nan_in_container(self, obj):
        """Recursively handle NaN values in containers"""
        if isinstance(obj, dict):
            return {k: self._handle_nan_in_container(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._handle_nan_in_container(item) for item in obj]
        if self._is_nan(obj):
            return None
        return obj


def save_json(data: dict, filename: str):
    """Save data to JSON file with proper formatting and NaN handling"""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, cls=NaNEncoder, indent=4, ensure_ascii=False)


def load_json(file_path: str) -> dict:
    """Load data from JSON file with proper NaN handling"""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_data(file_path):
    data = None
    if file_path:
        if file_path.endswith(".xlsx"):
            data = extract.read_xlsx(file_path)
        elif file_path.endswith(".zip"):
            data = extract.read_zip(file_path)
        elif file_path.endswith(".json"):
            data = load_json(file_path)
    return data


def display_graph_stats(G):
    """Display graph statistics"""
    stats = {
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "node_types": {},
        "edge_types": {},
    }

    # Count node types
    for node, attrs in G.nodes(data=True):
        node_type = attrs.get("type", "Unknown")
        stats["node_types"][node_type] = stats["node_types"].get(node_type, 0) + 1

    # Display node statistics
    st.subheader("Node Statistics")
    st.write(f"Total Nodes: {stats['total_nodes']}")
    if stats["node_types"]:
        nodes_df = pd.DataFrame(
            [
                {
                    "Node Type": type_name.replace("_", " ").title(),
                    "Count": count,
                    "Percentage": f"{(count/stats['total_nodes'])*100:.1f}%",
                }
                for type_name, count in stats["node_types"].items()
            ]
        )
        st.dataframe(
            nodes_df,
            hide_index=True,
            use_container_width=True,
        )

    # Count and display edge types if present
    if G.number_of_edges() > 0:
        st.subheader("Edge Statistics")
        st.write(f"Total Edges: {stats['total_edges']}")
        for edge in G.edges(data=True):
            edge_type = edge[2].get("type", "Unknown")
            stats["edge_types"][edge_type] = stats["edge_types"].get(edge_type, 0) + 1

        if stats["edge_types"]:
            edges_df = pd.DataFrame(
                [
                    {
                        "Edge Type": rel_name.replace("_", " ").title(),
                        "Count": count,
                        "Percentage": f"{(count/stats['total_edges'])*100:.1f}%",
                    }
                    for rel_name, count in stats["edge_types"].items()
                ]
            )
            st.dataframe(
                edges_df,
                hide_index=True,
                use_container_width=True,
            )


def display_graph(G):
    """Display interactive graph visualization"""
    # Visualization settings
    num_items = st.slider(
        "Number of random items to show",
        min_value=2,
        max_value=min(15, G.number_of_nodes()),
        value=min(5, G.number_of_nodes()),
        help="Select how many random items to visualize",
    )

    # Select random nodes and visualize
    selected_nodes = random.sample(list(G.nodes()), num_items)
    fig = transform.visualize_graph(G, selected_nodes)
    st.plotly_chart(fig, use_container_width=True)

    # Graph explanation
    with st.expander("Graph Legend"):
        st.markdown(
            """
        - **Nodes**: Represent entities in the graph
        - **Edges**: Show relationships between nodes
        - **Colors**: Different colors represent different types of nodes
        - **Lines**: Show connections between related nodes
        """
        )


def main():
    # Initialize graph server
    graph_server = load.GraphServer()

    file_path = input()

    data = None
    if file_path:
        data = extract_data(file_path)

    if data:
        st.header("Extracted Data")
        st.success("Data extracted successfully!")

        # Data view and download
        cols = st.columns([8, 1])
        with cols[0]:
            with st.expander("View Raw Data"):
                st.json(data)
        with cols[1]:
            # Save with proper NaN handling and indentation
            json_str = json.dumps(data, cls=NaNEncoder, indent=4, ensure_ascii=False)
            st.download_button(
                "Download JSON",
                data=json_str,
                file_name="data.json",
                mime="application/json",
            )

        st.header("Transformed Data")
        # Create the graph and display statistics
        G = transform.create_graph(data)
        st.success("Graph created successfully!")
        display_graph_stats(G)

        # Graph visualization section
        st.subheader("Graph Visualization")
        display_graph(G)

        # Server upload section
        st.header("Upload to Server")

        # Server health check
        server_status = graph_server.health_check()
        if server_status:
            st.success("✅ Server is healthy and ready to accept data")
        else:
            st.error("❌ Server is not available")
            st.info("Please check if the server is running and try again later.")
            st.stop()  # Stop execution if server is not healthy

        # Show available versions
        with st.expander("View Available Versions"):
            versions = graph_server.get_versions()
            if versions:
                st.write("Existing versions on server:")
                version_table = []
                for v in versions:
                    version_table.append({"Version": v})
                st.table(version_table)
            else:
                st.info("No versions found on server")

            st.markdown(
                """
            **Version Naming Guidelines:**
            - Use semantic versioning (e.g., v1, v2, v1.0.1)
            - Avoid special characters except hyphen (-)
            - Make it descriptive (e.g., v1-test, v1-prod)
            
            **Reserved Versions:**
            - `default`: System default version
            """
            )

        # Version input and upload button
        col1, col2 = st.columns([3, 1])
        with col1:
            default_version = (
                f"v1-test-{len(versions) + 1}"  # Suggest next version number
            )
            version = st.text_input("Version name", default_version)
            if version.lower() == "default":
                st.error("❌ Cannot use 'default' as version name - it is reserved")
                st.stop()
            if version in versions:
                st.warning(
                    f"⚠️ Version '{version}' already exists. Using this version will update existing data."
                )
        with col2:
            upload_button = st.button(
                "Upload to Server", disabled=version.lower() == "default"
            )

        if upload_button:
            try:
                progress = st.progress(0)

                def update_progress(value):
                    progress.progress(value)

                success, message = graph_server.send_graph(
                    graph=G,
                    version=version,
                    timestamp=0,
                    progress_callback=update_progress,
                )

                if success:
                    st.success(message)
                else:
                    st.error(message)
            except Exception as e:
                st.error(f"Error sending graph to server: {str(e)}")


main()
