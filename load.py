import requests
import json
import networkx as nx
from typing import Dict, Any, List, Tuple
import logging
import time
import copy
import numpy as np
import pandas as pd
import streamlit as st

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NaNEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle NaN, Infinity, and -Infinity values"""
    def default(self, obj):
        if isinstance(obj, float) and (np.isnan(obj) or pd.isna(obj)):
            return None
        if isinstance(obj, float) and np.isinf(obj):
            return "Infinity" if obj > 0 else "-Infinity"
        if isinstance(obj, (np.integer, np.floating)):
            return int(obj) if isinstance(obj, np.integer) else float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if pd.isna(obj):
            return None
        return super().default(obj)

class GraphServer:
    def __init__(self, base_url: str = "http://localhost:8000/api"):
        self.base_url = base_url.rstrip("/")
        
    def _make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make HTTP request to server"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            logger.info(f"Making {method} request to {url}")
            if data:
                logger.info(f"Request payload: action={data.get('action')}, type={data.get('type')}, timestamp={data.get('timestamp')}")
                logger.info(f"Payload size: {len(data.get('payload', []))} items")
            
            if method.lower() == "get":
                response = requests.get(url)
            elif method.lower() == "post":
                # Convert data to JSON with NaN handling
                json_data = json.dumps(data, cls=NaNEncoder)
                response = requests.post(url, json=json.loads(json_data))
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            logger.info(f"Response status: {response.status_code}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making {method} request to {url}: {str(e)}")
            logger.error(f"Response content: {getattr(e.response, 'content', 'No content')}")
            raise

    def send_graph(self, graph: nx.Graph, version: str, timestamp: int = 0, 
                  batch_size: int = 1000, progress_bar=None, is_first_timestamp: bool = True) -> Tuple[bool, str]:
        """Send graph data to server in batches with progress tracking"""
        try:
            # Convert graph to node and edge lists
            nodes_list = []
            edges_list = []
            
            # Process nodes
            for node, attrs in graph.nodes(data=True):
                node_data = {
                    "node_id": str(node),
                    "node_type": attrs.get("type", "default"),
                    "label": attrs.get("label", str(node)),
                    "properties": {}
                }
                # Handle NaN values in attributes
                for k, v in attrs.items():
                    if k not in ["type", "label"]:  # Skip already processed attributes
                        if isinstance(v, float) and (np.isnan(v) or pd.isna(v)):
                            node_data["properties"][k] = None
                        elif isinstance(v, float) and np.isinf(v):
                            node_data["properties"][k] = "Infinity" if v > 0 else "-Infinity"
                        else:
                            node_data["properties"][k] = v
                
                nodes_list.append(node_data)
            
            # Process edges
            for source, target, attrs in graph.edges(data=True):
                edge_data = {
                    "source_id": str(source),
                    "target_id": str(target),
                    "edge_type": attrs.get("type", "default"),
                    "label": attrs.get("label", f"{source}->{target}"),
                    "properties": {}
                }
                # Handle NaN values in attributes
                for k, v in attrs.items():
                    if k not in ["type", "label"]:  # Skip already processed attributes
                        if isinstance(v, float) and (np.isnan(v) or pd.isna(v)):
                            edge_data["properties"][k] = None
                        elif isinstance(v, float) and np.isinf(v):
                            edge_data["properties"][k] = "Infinity" if v > 0 else "-Infinity"
                        else:
                            edge_data["properties"][k] = v
                
                edges_list.append(edge_data)

            total_items = len(nodes_list) + len(edges_list)
            current_progress = 0
            
            logger.info(f"Sending {len(nodes_list)} nodes and {len(edges_list)} edges")
            
            # Use bulk_create for first timestamp, bulk_update for others
            action = "bulk_create" if is_first_timestamp else "bulk_update"
            logger.info(f"Using {action} for timestamp {timestamp}")

            # Send nodes in batches
            for i in range(0, len(nodes_list), batch_size):
                batch = nodes_list[i:i + batch_size]
                payload = {
                    "version": version,
                    "action": action,
                    "type": "schema",
                    "timestamp": timestamp,
                    "payload": batch
                }
                self._make_request("post", "schema/live/update", payload)
                time.sleep(0.1)  # Small delay between batches
                
                current_progress += len(batch)
                if progress_bar is not None:
                    progress_bar.progress(current_progress / total_items)
                logger.info(f"Uploaded {current_progress}/{total_items} items")

            # Send edges in batches
            for i in range(0, len(edges_list), batch_size):
                batch = edges_list[i:i + batch_size]
                payload = {
                    "version": version,
                    "action": action,
                    "type": "schema",
                    "timestamp": timestamp,
                    "payload": batch
                }
                self._make_request("post", "schema/live/update", payload)
                time.sleep(0.1)  # Small delay between batches
                
                current_progress += len(batch)
                if progress_bar is not None:
                    progress_bar.progress(current_progress / total_items)
                logger.info(f"Uploaded {current_progress}/{total_items} items")

            return True, f"Successfully sent {total_items} items ({len(nodes_list)} nodes, {len(edges_list)} edges)"
        except Exception as e:
            logger.error(f"Error sending graph: {str(e)}")
            return False, f"Error sending graph: {str(e)}"

    def get_versions(self) -> List[str]:
        """Get list of available versions from server"""
        try:
            response = requests.get(f"{self.base_url}/versions")
            response.raise_for_status()
            versions = response.json()
            if isinstance(versions, list):
                return sorted(versions)
            return []
        except Exception as e:
            logger.error(f"Error getting versions: {str(e)}")
            return []

    def health_check(self) -> bool:
        """Check if server is healthy"""
        try:
            response = self._make_request("get", "health")
            return response.get("status") == "healthy"
        except:
            return False

def upload_to_server(data: Dict[str, Any], version: str = "v1", batch_size: int = 1000, is_first_timestamp: bool = True) -> Dict[str, Any]:
    """
    Upload graph data to server using the GraphServer class
    
    Args:
        data: Dictionary containing timestamp and graph data
        version: Version string for the upload
        batch_size: Number of items to send in each batch
        is_first_timestamp: Whether this is the first timestamp being uploaded
        
    Returns:
        Dictionary with upload status
    """
    try:
        logger.info(f"Starting upload for timestamp {data['timestamp']} (is_first_timestamp={is_first_timestamp})")
        
        # Initialize GraphServer
        server = GraphServer()
        
        # Check server health
        if not server.health_check():
            logger.error("Server health check failed")
            return {
                "success": False,
                "error": "Server is not healthy"
            }
        
        # Get graph and timestamp from data
        graph = nx.node_link_graph(data["graph"])
        timestamp = int(data["timestamp"])
        
        logger.info(f"Graph info: Nodes={len(graph.nodes)}, Edges={len(graph.edges)}")
        
        # Create progress bar
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        
        try:
            # Send graph to server
            success, message = server.send_graph(
                graph=graph,
                version=version,
                timestamp=timestamp,
                batch_size=batch_size,
                progress_bar=progress_bar,
                is_first_timestamp=is_first_timestamp
            )
            
            logger.info(f"Upload completed: success={success}, message={message}")
            
            if success:
                return {"success": True, "message": message}
            else:
                return {"success": False, "error": message}
        finally:
            # Clean up progress bar
            progress_bar.empty()
            status_text.empty()
            
    except Exception as e:
        error = f"Upload error: {str(e)}"
        logger.error(error, exc_info=True)
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }