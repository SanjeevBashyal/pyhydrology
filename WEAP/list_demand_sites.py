
import win32com.client

WEAP_AREA = "Ghunsa"

def main():
    print("Connecting to WEAP...")
    try:
        weap = win32com.client.Dispatch("WEAP.WEAPApplication")
        
        if weap.ActiveArea.Name != WEAP_AREA:
            weap.ActiveArea = WEAP_AREA
            
        print("Listing Demand Sites (Type 2):")
        count = 0
        for branch in weap.Branches:
            if branch.TypeId == 2:
                print(f" - {branch.Name}")
                count += 1
        
        if count == 0:
            print("No Demand Sites found.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
