
import pandas as pd
import win32com.client
import os

WEAP_AREA = "Ghunsa"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTLEMENTS_FILE = os.path.join(BASE_DIR, "settlements.csv")

def main():
    print("Connecting to WEAP...")
    try:
        weap = win32com.client.Dispatch("WEAP.WEAPApplication")
        if weap.ActiveArea.Name != WEAP_AREA:
            weap.ActiveArea = WEAP_AREA
            
        df = pd.read_csv(SETTLEMENTS_FILE, encoding='utf-8-sig')
        df.columns = [c.strip() for c in df.columns]
        
        print("\nChecking Settlement Branches:")
        for loc in df['Location']:
            try:
                branch = weap.Branch(loc)
                print(f" - '{loc}': TypeId {branch.TypeId}, Class '{branch.TypeName}'")
            except:
                print(f" - '{loc}': Not found")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
