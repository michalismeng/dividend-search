import pandas as pd
import argparse

parser = argparse.ArgumentParser(
                    prog='read_data',
                    description='Produce HTML from CSV file with financial metrics')
parser.add_argument("filename", help="Input CSV file containing the parsed metrics")
parser.add_argument("--filter", action=argparse.BooleanOptionalAction, default=True, help="Apply any filters to dataset")

args = parser.parse_args()

df = pd.read_csv(args.filename)

if args.filter:
    df = df[df["comment"] == "ok"]
    df = df[df["growth_yy"] > 0.07]
    df = df[df["Debt Ratio"] < 5]
    df = df[df["ROE"] > 0]
    df = df[df["Sector"].str.contains("Financial Services") == False]

cols = list(df.columns[0:list(df.columns).index("outliers")]) + list(df.columns[list(df.columns).index("outliers") + 1:]) + ["outliers"]
df = df[cols]
df = df.sort_values(by="symbol")

print(df.to_html(index=False))