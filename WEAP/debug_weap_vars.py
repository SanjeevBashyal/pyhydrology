
import win32com.client

WEAP_AREA = "Ghunsa"
TARGET_BRANCH = "Ghunsa_Khola_Hydropower_Project"

def main():
    print("Connecting to WEAP...")
    try:
        weap = win32com.client.Dispatch("WEAP.WEAPApplication")
        
        if weap.ActiveArea.Name != WEAP_AREA:
            weap.ActiveArea = WEAP_AREA
            
        print(f"Looking for branch: {TARGET_BRANCH}")
        try:
            branch = weap.Branch(TARGET_BRANCH)
            print(f"Found branch: {branch.Name}, TypeId: {branch.TypeId}")
            
            with open("debug_vars.txt", "w") as f:
                f.write(f"Branch: {branch.Name}\n")
                f.write("Variables:\n")
                for var in branch.Variables:
                     f.write(f" - Name: '{var.Name}', ID: {var.Id}\n")
            print("Wrote variables to debug_vars.txt")
                
        except Exception as e:
            print(f"Branch not found or error: {e}")

    except Exception as e:
        print(f"WEAP Error: {e}")

if __name__ == "__main__":
    main()
