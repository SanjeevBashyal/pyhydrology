
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

def plot_sensitivity():
    input_file = Path("sensitivity_results.csv")
    output_file = Path("sensitivity_plot.png")
    
    if not input_file.exists():
        print(f"File not found: {input_file}")
        return

    # Read data
    df = pd.read_csv(input_file)
    
    # Sort by sensitivity descending
    df = df.sort_values(by="1st Order Sensitivity", ascending=True)
    
    # Create plot
    plt.figure(figsize=(10, 8))
    
    # Create horizontal bar chart
    bars = plt.barh(df['Name'], df['1st Order Sensitivity'], color='skyblue', edgecolor='black')
    
    # Add labels and title
    plt.xlabel('1st Order Sensitivity Index', fontsize=12)
    plt.ylabel('Parameter Name', fontsize=12)
    plt.title('SWAT+ Parameter Sensitivity Analysis', fontsize=14, fontweight='bold')
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    
    # Add value labels to the end of each bar
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 0.005, bar.get_y() + bar.get_height()/2, 
                 f'{width:.3f}', 
                 va='center', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    print(f"Sensitivity plot saved to: {output_file}")

def plot_hru_analysis():
    input_file = Path("hru.csv")
    output_file = Path("hru_plot.png")
    
    if not input_file.exists():
        print(f"File not found: {input_file}")
        return

    # Read data - handle potential tab separation if comma fails, but try default first
    try:
        df = pd.read_csv(input_file, sep=None, engine='python')
    except Exception:
        df = pd.read_csv(input_file)
    
    # Clean column names
    df.columns = [c.strip() for c in df.columns]
    
    # Identify columns (assuming first is HRUs, second is NSE)
    x_col = df.columns[0]
    y_col = df.columns[1]
    
    # Sort by HRUs to ensure line connects correctly
    df = df.sort_values(by=x_col)
    
    # Create plot
    plt.figure(figsize=(10, 6))
    
    plt.plot(df[x_col], df[y_col], marker='o', linestyle='-', linewidth=2, markersize=8, color='royalblue')
    
    # Add labels and title
    plt.xlabel('Number of HRUs', fontsize=12)
    plt.ylabel('Calibration NSE', fontsize=12)
    plt.title('Effect of HRU Definition on Model Performance', fontsize=14, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Annotate points
    for i, row in df.iterrows():
        plt.annotate(f'{row[y_col]:.3f}', 
                     (row[x_col], row[y_col]),
                     textcoords="offset points", 
                     xytext=(0,10), 
                     ha='center')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300)
    print(f"HRU plot saved to: {output_file}")

if __name__ == "__main__":
    # Set style
    plt.style.use('ggplot')
    
    print("Generating plots...")
    plot_sensitivity()
    plot_hru_analysis()
    print("Done.")
