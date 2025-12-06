import pandas as pd

df = pd.read_excel("stage_weights.xlsx", engine="openpyxl")

print("SHEET NAME:", pd.ExcelFile("stage_weights.xlsx").sheet_names)
print("\nHEADERS:")
print(df.columns.tolist())

print("\nFIRST 10 ROWS:")
print(df.head(10))
