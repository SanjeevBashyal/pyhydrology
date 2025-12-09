import win32com.client
import shapefile
import os

# --- CONFIGURATION ---
# Path to your demand nodes shapefile (must be POINT type)
SHAPEFILE_PATH = r"E:\5 Nexus\4 WEAP\1 Map Schematic\ror.shp"
# The exact name of your WEAP Area (must be open in WEAP)
WEAP_AREA_NAME = "Ghunsa"
# The name of the attribute field in your shapefile containing the demand site names
DEMAND_NAME_FIELD = "Name"
# The type of node to create (from WEAP API: "Demand Site", "Catchment", "Reservoir", "Run of River Hydro", etc.)
# Common node types and their default priorities:
# - "Demand Site": Priority 1 (default)
# - "Catchment": Priority 1 (default)
# - "Reservoir": Priority 99 (default)
# - "Run of River Hydro": Priority 99 (default)
# - "Groundwater": Priority 1 (default)
NODE_TYPE = "Run of River Hydro"
# Set to True to delete all existing nodes of this type before creating new ones
DELETE_EXISTING_NODES = True
# Optional: River name to place nodes on (use "N/A" to force local placement)
# For "Run of River Hydro", you may want to specify a river name to place it on a river
# For other node types, use "N/A" for local placement
RIVER_NAME = "N/A"
# Optional: Priority for nodes (default 1, but 99 for reservoirs and hydro)
# Note: WEAP automatically sets Reservoir and Run of River Hydro to priority 99
PRIORITY = 99  # Set to 99 for Run of River Hydro as per WEAP defaults
# Optional: Whether the node is active in base year (default True)
ACTIVE_IN_BASE_YEAR = True
# Optional: Map label (leave blank for default, or specify custom label)
# Use " " (single space) to hide labels on the schematic
MAP_LABEL = ""

# --- SCRIPT LOGIC ---

def automate_demand_creation():
    """
    Connects to WEAP, reads a point shapefile, and creates demand nodes.
    Assumes the shapefile contains POINT features with demand site information.
    """
    print("Starting WEAP demand node creation workflow...")

    # Validate that the shapefile exists
    if not os.path.exists(SHAPEFILE_PATH):
        print(f"Error: Shapefile not found at {SHAPEFILE_PATH}")
        return

    weap = None
    try:
        # 1. Connect to the WEAP Application via the COM API
        print("Connecting to WEAP...")
        # This connects to a running instance of WEAP
        weap = win32com.client.Dispatch("WEAP.WEAPApplication")
        weap.Visible = True # Makes the WEAP window visible

        # Set the active area
        weap.ActiveArea = WEAP_AREA_NAME
        print(f"Successfully connected to WEAP Area: {weap.ActiveArea.Name}")
        
        # Turn off screen updating for performance while creating many objects
        weap.ScreenUpdating = False

        # 2. Delete existing nodes of the specified type if requested
        if DELETE_EXISTING_NODES:
            print(f"Deleting existing {NODE_TYPE} objects...")
            try:
                # Get the TypeID for the node type
                type_id_map = {
                    "Demand Site": 1,
                    "Catchment": 21,
                    "Reservoir": 4,
                    "Groundwater": 3,
                    "Other Supply": 5,
                    "Flow Requirement": 9,
                    "River Withdrawal": 10,
                    "Tributary Inflow": 13,
                    "Run of River Hydro": 14,
                    "Diversion": 15,
                    "River Reach": 16,
                    "Return Flow Node": 17,
                    "Streamflow Gauge": 20,
                    "Catchment Inflow Node": 23
                }
                
                type_id = type_id_map.get(NODE_TYPE, NODE_TYPE)
                print(f"  - Looking for nodes of type: {NODE_TYPE} (ID: {type_id})")
                
                # Get all nodes of the specified type
                nodes = weap.BranchesOfType(type_id)
                if nodes and len(nodes) > 0:
                    print(f"  - Found {len(nodes)} existing {NODE_TYPE} objects")
                    
                    # Delete each node
                    for i in range(len(nodes)):
                        try:
                            node = nodes[i]
                            node_name = getattr(node, 'Name', f'{NODE_TYPE}_{i}')
                            print(f"    - Deleting {NODE_TYPE}: {node_name}")
                            node.Delete()
                        except Exception as e:
                            print(f"    - Warning: Could not delete {NODE_TYPE} {i}: {e}")
                            continue
                    
                    print(f"  - Successfully deleted existing {NODE_TYPE} objects")
                else:
                    print(f"  - No existing {NODE_TYPE} objects found")
                    
            except Exception as e:
                print(f"  - Warning: Error while deleting existing {NODE_TYPE} objects: {e}")
                print("  - Continuing with node creation...")

        # 3. Read the Shapefile
        print(f"Reading shapefile: {SHAPEFILE_PATH}")
        sf = shapefile.Reader(SHAPEFILE_PATH)

        # Ensure the shapefile is of point type
        if sf.shapeType != shapefile.POINT and sf.shapeType != shapefile.POINTZ:
            print(f"Error: Shapefile must be a POINT type, but it is type {sf.shapeType}")
            return

        # Get the index of the name field
        field_names = [field[0] for field in sf.fields[1:]] # Skip deletion flag
        try:
            name_field_index = field_names.index(DEMAND_NAME_FIELD)
        except ValueError:
            print(f"Error: Field '{DEMAND_NAME_FIELD}' not found in shapefile.")
            print(f"Available fields: {field_names}")
            return

        # 4. Create WEAP Demand Node objects from each point feature
        for i, shaperec in enumerate(sf.iterShapeRecords()):
            shape = shaperec.shape
            record = shaperec.record

            node_name = str(record[name_field_index])
            
            # Clean node_name: remove special characters and replace spaces with underscores
            import re
            # Replace spaces with underscores
            node_name = node_name.replace(" ", "_")
            # Remove special characters except letters, numbers, and underscores
            node_name = re.sub(r'[^a-zA-Z0-9_]', '', node_name)
            # Ensure it starts with a letter (WEAP requirement)
            if node_name and not node_name[0].isalpha():
                node_name = f"{NODE_TYPE.replace(' ', '')}_{node_name}"

            print(f"Processing {NODE_TYPE}: {node_name}")

            # A. Extract geometry coordinates (point has only one coordinate pair)
            point = shape.points[0]  # Get the single point
            x_coord = point[0]
            y_coord = point[1]

            print(f"  - Coordinates: ({x_coord:.4f}, {y_coord:.4f})")

            # B. Create the Node object using CreateNode API per WEAP documentation
            # CreateNode(TypeNameOrID, X, Y, Name, MapLabel, ActiveInBaseYear, Priority, IsIrrigated, River)
            try:
                if NODE_TYPE == "Demand Site":
                    # For Demand Sites, include Priority
                    node_obj = weap.CreateNode(NODE_TYPE, x_coord, y_coord, node_name, MAP_LABEL, ACTIVE_IN_BASE_YEAR, PRIORITY)
                elif NODE_TYPE == "Catchment":
                    # For Catchments, include IsIrrigated parameter
                    node_obj = weap.CreateNode(NODE_TYPE, x_coord, y_coord, node_name, MAP_LABEL, ACTIVE_IN_BASE_YEAR, PRIORITY, False)
                elif NODE_TYPE == "Reservoir":
                    # For Reservoirs, include Priority (defaults to 99)
                    node_obj = weap.CreateNode(NODE_TYPE, x_coord, y_coord, node_name, MAP_LABEL, ACTIVE_IN_BASE_YEAR, PRIORITY)
                elif NODE_TYPE == "Run of River Hydro":
                    # For Run of River Hydro, include Priority (defaults to 99)
                    # Note: Run of River Hydro nodes are typically placed on rivers
                    if RIVER_NAME != "N/A":
                        node_obj = weap.CreateNode(NODE_TYPE, x_coord, y_coord, node_name, MAP_LABEL, ACTIVE_IN_BASE_YEAR, PRIORITY, False, False, RIVER_NAME)
                    else:
                        node_obj = weap.CreateNode(NODE_TYPE, x_coord, y_coord, node_name, MAP_LABEL, ACTIVE_IN_BASE_YEAR, PRIORITY)
                else:
                    # For other node types, use basic parameters
                    node_obj = weap.CreateNode(NODE_TYPE, x_coord, y_coord, node_name, MAP_LABEL, ACTIVE_IN_BASE_YEAR)
                
                print(f"  - Successfully created {NODE_TYPE}: {node_name}")
                
            except Exception as e:
                print(f"  - Error creating {NODE_TYPE} '{node_name}': {e}")
                continue

        # Turn screen updating back on and refresh the view
        weap.ScreenUpdating = True
        # Refresh the schematic view
        try:
            weap.ZoomSchematic()
        except Exception:
            # Fallback to other zoom methods if available
            try:
                if hasattr(weap, "Schematic") and hasattr(weap.Schematic, "ZoomToFit"):
                    weap.Schematic.ZoomToFit()
                elif hasattr(weap, "ZoomToFit"):
                    weap.ZoomToFit()
            except Exception:
                print("  - Note: Could not zoom to fit; you may need to manually adjust the view")
        print("\nWorkflow completed successfully!")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Re-enable screen updating if an error occurred mid-way
        if weap and not weap.ScreenUpdating:
            weap.ScreenUpdating = True
            
        # It's good practice to release the COM object
        weap = None
        print("Script finished.")


# --- Run the main function ---
if __name__ == "__main__":
    automate_demand_creation()
