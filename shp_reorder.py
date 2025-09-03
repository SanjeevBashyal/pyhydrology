import shapefile
import sys

def reorder_river_network(input_shp_path, output_shp_path):
    """
    Rearranges the features of a line shapefile based on connectivity
    to create continuous paths, mimicking a river network.

    Args:
        input_shp_path (str): The file path for the input line shapefile.
        output_shp_path (str): The file path for the new, ordered shapefile.
    """
    try:
        # 1. READ THE INPUT SHAPEFILE
        print(f"Reading input shapefile: {input_shp_path}")
        sf = shapefile.Reader(input_shp_path)
        
        if sf.shapeType != shapefile.POLYLINE:
            print("Error: Input shapefile must be of type POLYLINE.")
            return

        # Load all shapes and records into a list of dictionaries for easier handling.
        # We also add a 'visited' flag to track which segments have been processed.
        features = []
        for i in range(len(sf)):
            shape_rec = sf.shapeRecord(i)
            features.append({
                'shape': shape_rec.shape,
                'record': shape_rec.record,
                'visited': False,
                'original_index': i 
            })
            
        print(f"Loaded {len(features)} features.")

    except shapefile.ShapefileException as e:
        print(f"Error reading shapefile: {e}")
        return

    # This will hold the final, ordered list of features
    ordered_features = []
    
    # 2. TRAVERSE THE NETWORK AND BUILD CONNECTED PATHS
    for i in range(len(features)):
        # If this feature has already been added to a path, skip it
        if features[i]['visited']:
            continue

        # Start a new path with the current feature
        current_path = [features[i]]
        features[i]['visited'] = True
        
        print(f"\nStarting a new path with original feature #{features[i]['original_index']}")

        # Continuously try to extend the path at its head or tail
        while True:
            path_extended = False
            
            # The endpoints of our current continuous path
            path_head_coord = current_path[0]['shape'].points[0]
            path_tail_coord = current_path[-1]['shape'].points[-1]

            # Search for an unvisited feature to connect to our path
            for j in range(len(features)):
                if features[j]['visited']:
                    continue

                candidate_feature = features[j]
                candidate_start_coord = candidate_feature['shape'].points[0]
                candidate_end_coord = candidate_feature['shape'].points[-1]

                # Check for connections and extend the path
                
                # Case 1: Candidate connects to the TAIL of our path (forward)
                if candidate_start_coord == path_tail_coord:
                    current_path.append(candidate_feature)
                    features[j]['visited'] = True
                    path_extended = True
                    print(f" -> Appended feature #{candidate_feature['original_index']}")
                    break # Restart search with the newly extended path
                
                # Case 2: Candidate connects to the TAIL (but is reversed)
                elif candidate_end_coord == path_tail_coord:
                    # Reverse the points of the candidate shape
                    candidate_feature['shape'].points.reverse()
                    current_path.append(candidate_feature)
                    features[j]['visited'] = True
                    path_extended = True
                    print(f" -> Appended (and reversed) feature #{candidate_feature['original_index']}")
                    break

                # Case 3: Candidate connects to the HEAD of our path
                elif candidate_end_coord == path_head_coord:
                    current_path.insert(0, candidate_feature)
                    features[j]['visited'] = True
                    path_extended = True
                    print(f" <- Prepended feature #{candidate_feature['original_index']}")
                    break
                    
                # Case 4: Candidate connects to the HEAD (but is reversed)
                elif candidate_start_coord == path_head_coord:
                    candidate_feature['shape'].points.reverse()
                    current_path.insert(0, candidate_feature)
                    features[j]['visited'] = True
                    path_extended = True
                    print(f" <- Prepended (and reversed) feature #{candidate_feature['original_index']}")
                    break
            
            # If we went through all features and couldn't extend the path, it's complete
            if not path_extended:
                print(f"Path finished with {len(current_path)} segments.")
                ordered_features.extend(current_path)
                break

    # 3. WRITE THE REORDERED FEATURES TO A NEW SHAPEFILE
    print(f"\nWriting {len(ordered_features)} reordered features to {output_shp_path}")
    with shapefile.Writer(output_shp_path, shapeType=sf.shapeType) as w:
        # Copy the fields (attributes) from the original shapefile
        w.fields = sf.fields[1:]  # Skip the first 'DeletionFlag' field

        # Write each feature in the new order
        for feature in ordered_features:
            w.shape(feature['shape'])
            w.record(*feature['record'])
            
    print("\nProcessing complete.")

# --- USAGE EXAMPLE ---
if __name__ == '__main__':
    # Create a dummy shapefile for testing if it doesn't exist
    try:
        sf_test = shapefile.Reader("./1 Data/River/main_river.shp")
    except shapefile.ShapefileException:
        print("Creating a dummy shapefile 'disordered_river.shp' for demonstration.")
        with shapefile.Writer("disordered_river.shp", shapefile.POLYLINE) as w:
            w.field("ID", "N")
            w.field("SEGMENT", "C")
            # This order is intentionally jumbled
            w.line([[[50, 50], [60, 60]]]); w.record(3, "Segment C") # Middle
            w.line([[[10, 10], [30, 30]]]); w.record(1, "Segment A") # Start
            w.line([[[60, 60], [80, 80]]]); w.record(4, "Segment D") # End
            w.line([[[30, 30], [50, 50]]]); w.record(2, "Segment B") # After A
            w.line([[[100, 100], [110, 110]]]); w.record(5, "Tributary 1") # Disconnected

    # Define your input and output file paths
    input_file = "./1 Data/River/main_river.shp"
    output_file = "./1 Data/River/main_river.shp"
    
    # Run the reordering function
    reorder_river_network(input_file, output_file)