# ETL Data Processing and Graph Visualization App

A Streamlit-based application for processing Excel/JSON data, transforming it into a graph structure, and sending it to a graph server. The app provides interactive visualization and data exploration capabilities.

## Features

- Data Import: Support for XLSX, JSON, and ZIP files
- Graph Transformation: Convert tabular data into a networked graph structure
- Interactive Visualization: View and explore the graph with customizable displays
- Server Integration: Upload graph data to a remote graph server
- Version Management: Track and manage different versions of uploaded data

## Setup and Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Virtual environment (recommended)

### Installation Steps

1. Clone the repository:
   ```bash
   git clone <repository-url> etl
   cd etl
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the application:
   ```bash
   streamlit run app.py
   ```

### Server Configuration

The app requires a graph server running at `http://localhost:8000`. Make sure the server is running before attempting to upload data.

## Architecture and Implementation

The application is structured into three main components:

### 1. Data Extraction (`extract.py`)

- Handles file uploads (XLSX, JSON, ZIP)
- Processes raw data into a standardized dictionary format
- Manages data validation and cleaning
- Handles NaN values and data type conversions

### 2. Data Transformation (`transform.py`)

- Converts dictionary data into a NetworkX graph structure
- Creates nodes for each unique entity
- Establishes edges based on relationships
- Implements graph visualization using Plotly
- Calculates graph statistics and metrics

### 3. Data Loading (`load.py`)

- Manages communication with the graph server
- Handles data serialization and batch processing
- Implements version control and error handling
- Provides server health monitoring

## Data Flow

1. **File Upload and Extraction**
   - User uploads a file through the Streamlit interface
   - File is validated and processed based on type
   - Data is extracted into a standardized dictionary format

2. **Graph Creation**
   - Dictionary data is analyzed for relationships
   - Nodes are created for unique entities
   - Edges are established based on relationships
   - Graph attributes are assigned (types, labels, properties)

3. **Server Upload**
   - Graph data is serialized into the server's expected format
   - Data is split into batches for efficient processing
   - Nodes and edges are sent separately
   - Progress is tracked and displayed to the user

## Data Structures

### Node Format
```json
{
    "node_id": "unique_identifier",
    "node_type": "type_name",
    "label": "display_label",
    "properties": {
        "attribute1": "value1",
        "attribute2": "value2"
    }
}
```

### Edge Format
```json
{
    "source_id": "source_node_id",
    "target_id": "target_node_id",
    "edge_type": "relationship_type",
    "label": "relationship_label",
    "properties": {
        "attribute1": "value1",
        "attribute2": "value2"
    }
}
```

## Version Management

- Versions are used to track different iterations of the graph data
- Reserved version names: "default"
- Versions can be viewed and selected before upload
- Existing versions can be updated with new data

## Error Handling

The application implements comprehensive error handling:

- File validation and format checking
- NaN value handling in data processing
- Server communication error handling
- Version conflict management
- Progress tracking and user feedback

## User Interface

The Streamlit interface provides:

1. **Data Upload Section**
   - File upload widget
   - Data preview
   - Download processed JSON

2. **Graph Visualization**
   - Interactive graph display
   - Node and edge statistics
   - Customizable visualization options

3. **Server Upload**
   - Server health status
   - Version management
   - Upload progress tracking
   - Success/error feedback

## Detailed Implementation

### Graph Creation Algorithm

The graph creation process in `transform.py` follows these steps:

1. **Node Creation**
   ```python
   def create_graph(data: Dict[str, List[Dict[str, Any]]]) -> nx.Graph:
   ```
   - Input is a dictionary where keys are type names and values are lists of items
   - For each item in each type:
     - Creates a unique node ID using format: `type_name_identifier`
     - Identifier is chosen from 'id', 'Part', 'Name' fields, or hash of item
     - Adds node to graph with type and all item properties

2. **Edge Creation - Same Type**
   - For each type in the data:
     - Takes all possible pairs of items using `combinations`
     - Finds matching string values between items using `find_matching_strings`
     - If matches found:
       - Creates edge between nodes
       - Sets relationship as `same_type_matches`
       - Stores matching fields in edge properties

3. **Edge Creation - Different Types**
   - For each pair of different types:
     - Compares all items between the two types
     - Finds matching string values
     - If matches found:
       - Creates edge with relationship `type1_type2_match`
       - Stores matching fields in edge properties

4. **String Matching Algorithm**
   ```python
   def find_matching_strings(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> List[str]:
   ```
   - Compares all key-value pairs between two dictionaries
   - Matches only string values (case-insensitive)
   - Returns list of matches in format "key=value"

### Example Graph Structure

For input data:
```python
data = {
    "Person": [
        {"id": "1", "name": "John", "department": "Engineering"},
        {"id": "2", "name": "Alice", "department": "Engineering"}
    ],
    "Department": [
        {"id": "eng", "name": "Engineering", "location": "Building A"}
    ]
}
```

The algorithm creates:
1. **Nodes**:
   - `Person_1`: {type: "Person", id: "1", name: "John", department: "Engineering"}
   - `Person_2`: {type: "Person", id: "2", name: "Alice", department: "Engineering"}
   - `Department_eng`: {type: "Department", id: "eng", name: "Engineering", location: "Building A"}

2. **Edges**:
   - Between `Person_1` and `Person_2`:
     - relationship: "same_Person_matches"
     - matches: ["department=Engineering"]
   - Between `Person_1` and `Department_eng`:
     - relationship: "Person_Department_match"
     - matches: ["department=Engineering", "name=Engineering"]
   - Between `Person_2` and `Department_eng`:
     - relationship: "Person_Department_match"
     - matches: ["department=Engineering", "name=Engineering"]

### Graph Statistics

The `get_graph_stats` function provides:
- Total number of nodes and edges
- Node count by type
- Edge count by relationship type
- Average degree (2 * edges / nodes)

### Visualization

The graph visualization uses:
1. Spring layout for node positioning
2. Color coding by node type
3. Interactive features:
   - Hover information for nodes and edges
   - Zoom and pan capabilities
   - Subgraph visualization for large graphs