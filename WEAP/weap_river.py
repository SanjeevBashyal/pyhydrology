import win32com.client
import shapefile
import os

# --- CONFIGURATION ---
# Path to your river network shapefile
SHAPEFILE_PATH = r"E:\5 Nexus\4 WEAP\1 Map Schematic\streams.shp"
# The exact name of your WEAP Area (must be open in WEAP)
WEAP_AREA_NAME = "Ghunsa"
# The name of the attribute field in your shapefile containing the river reach names
RIVER_NAME_FIELD = "LINKNO"
# Set to True to delete all existing river objects before creating new ones
DELETE_EXISTING_RIVER = True

# --- SCRIPT LOGIC ---

def automate_river_creation():
    """
    Connects to WEAP, reads a shapefile, and creates a river network.
    Assumes a simple, sequential network where features in the shapefile
    are ordered from upstream to downstream.
    """
    print("Starting WEAP river creation workflow...")

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

        # 2. Delete existing river objects if requested
        if DELETE_EXISTING_RIVER:
            print("Deleting existing river objects...")
            try:
                # Get all river branches using BranchesOfType(6) where 6 = River TypeID
                rivers = weap.BranchesOfType(6)  # 6 = River type ID per WEAP API
                if rivers and len(rivers) > 0:
                    print(f"  - Found {len(rivers)} existing river objects")
                    
                    # Delete each river branch
                    for i in range(len(rivers)):
                        try:
                            river = rivers[i]
                            river_name = getattr(river, 'Name', f'River_{i}')
                            print(f"    - Deleting river: {river_name}")
                            river.Delete()
                        except Exception as e:
                            print(f"    - Warning: Could not delete river {i}: {e}")
                            continue
                    
                    print(f"  - Successfully deleted existing river objects")
                else:
                    print("  - No existing river objects found")
                    
            except Exception as e:
                print(f"  - Warning: Error while deleting existing rivers: {e}")
                print("  - Continuing with river creation...")

        # 3. Read the Shapefile
        print(f"Reading shapefile: {SHAPEFILE_PATH}")
        sf = shapefile.Reader(SHAPEFILE_PATH)

        # Ensure the shapefile is of polyline type
        if sf.shapeType != shapefile.POLYLINE:
            print(f"Error: Shapefile must be a POLYLINE type, but it is type {sf.shapeType}")
            return

        # Get the index of the name field
        field_names = [field[0] for field in sf.fields[1:]] # Skip deletion flag
        try:
            name_field_index = field_names.index(RIVER_NAME_FIELD)
        except ValueError:
            print(f"Error: Field '{RIVER_NAME_FIELD}' not found in shapefile.")
            print(f"Available fields: {field_names}")
            return

        # 3. Create WEAP River objects from each polyline feature
        for i, shaperec in enumerate(sf.iterShapeRecords()):
            shape = shaperec.shape
            record = shaperec.record

            reach_name = str(record[name_field_index])
            
            # Clean reach_name: remove special characters and replace spaces with underscores
            import re
            # Replace spaces with underscores
            reach_name = reach_name.replace(" ", "_")
            # Remove special characters except letters, numbers, and underscores
            reach_name = re.sub(r'[^a-zA-Z0-9_]', '', reach_name)
            # Ensure it starts with a letter (WEAP requirement)
            if reach_name and not reach_name[0].isalpha():
                reach_name = "River_" + reach_name

            print(f"Processing reach: {reach_name}")

            # A. Extract geometry coordinates
            points = shape.points
            if len(points) < 2:
                print(f"  - Skipping reach '{reach_name}' because it has fewer than 2 points.")
                continue

            x_coords = tuple(p[0] for p in points)
            y_coords = tuple(p[1] for p in points)

            # B. Create the River object using CreateRiver API per WEAP documentation
            # CreateRiver(TypeNameOrID, X1, Y1, X2, Y2, Name, MapLabel, ActiveInBaseYear)
            # Returns a WEAPBranch object
            river_obj = weap.CreateRiver("River", x_coords[-1], y_coords[-1], x_coords[-2], y_coords[-2], reach_name)

            # C. Add intermediate vertices using WEAPBranch.AddPoint method
            # Skip first and last points as they're already set by CreateRiver
            # for j in range(1, len(points) - 1):
            for j in range(3, len(points)+1):
                try:
                    river_obj.AddPoint(x_coords[-j], y_coords[-j])
                    # print(f"    - Added intermediate vertex {j}: ({x_coords[j]:.4f}, {y_coords[j]:.4f})")
                except Exception as e:
                    print(f"    - Warning: Could not add vertex {j}: {e}")
                    # Continue with other vertices even if one fails
                    continue
            # break

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
    automate_river_creation()