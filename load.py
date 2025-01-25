import requests
import json
import networkx as nx
from typing import Dict, Any, List, Tuple
import logging
import time
import copy
import numpy as np
import pandas as pd

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
        return super().default(obj)

class GraphServer:
    def __init__(self, base_url: str = "http://localhost:8000/api"):
        self.base_url = base_url.rstrip("/")
        
    def _make_request(self, method: str, endpoint: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make HTTP request to server"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        try:
            if method.lower() == "get":
                response = requests.get(url)
            elif method.lower() == "post":
                # Convert data to JSON with NaN handling
                json_data = json.dumps(data, cls=NaNEncoder)
                response = requests.post(url, json=json.loads(json_data))
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making {method} request to {url}: {str(e)}")
            raise

    def send_graph(self, graph: nx.Graph, version: str, timestamp: int = 0, 
                  batch_size: int = 1000, progress_callback=None) -> Tuple[bool, str]:
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

            # Send nodes in batches
            for i in range(0, len(nodes_list), batch_size):
                batch = nodes_list[i:i + batch_size]
                payload = {
                    "version": version,
                    "action": "bulk_create",
                    "type": "schema",
                    "timestamp": timestamp,
                    "payload": batch
                }
                self._make_request("post", "schema/live/update", payload)
                time.sleep(1)  # Rate limiting
                
                current_progress += len(batch)
                if progress_callback:
                    progress_callback(current_progress / total_items)

            # Send edges in batches
            for i in range(0, len(edges_list), batch_size):
                batch = edges_list[i:i + batch_size]
                payload = {
                    "version": version,
                    "action": "bulk_create",
                    "type": "schema",
                    "timestamp": timestamp,
                    "payload": batch
                }
                self._make_request("post", "schema/live/update", payload)
                time.sleep(1)  # Rate limiting
                
                current_progress += len(batch)
                if progress_callback:
                    progress_callback(current_progress / total_items)

            return True, f"Successfully sent {total_items} items to server"
        except Exception as e:
            return False, f"Error sending graph to server: {str(e)}"

    def get_versions(self) -> List[str]:
        """Get list of available versions from server"""
        try:
            # Make direct request to versions endpoint
            response = requests.get(f"{self.base_url}/versions")
            response.raise_for_status()
            
            # Response is a JSON array of version strings
            versions = response.json()
            if isinstance(versions, list):
                return sorted(versions)  # Return sorted list for better display
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