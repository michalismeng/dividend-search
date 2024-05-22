import pandas as pd
import argparse
import jinja2 as j2

j2_env = j2.Environment()

parser = argparse.ArgumentParser(
                    prog='read_data',
                    description='Produce HTML from CSV file with financial metrics')
parser.add_argument("filename", help="Input CSV file containing the parsed metrics")
parser.add_argument("--filter", action=argparse.BooleanOptionalAction, default=True, help="Apply any filters to dataset")

args = parser.parse_args()

df = pd.read_csv(args.filename)

if args.filter:
    df = df[df["comment"] == "ok"]
    df = df[df["Net Margin"] > 0]
    df = df[df["Debt Ratio"] < 5]
    df = df[df["ROE"] > 0]
    df = df[df["Sector"].str.contains("Financial Services") == False]

cols = list(df.columns[0:list(df.columns).index("Outliers")]) + list(df.columns[list(df.columns).index("Outliers") + 1:]) + ["Outliers"]
df = df[cols]
df = df.sort_values(by="Symbol")

with open("template.html.j2") as f:
    template = j2_env.from_string(f.read())
print(template.render(table=df.to_html(index=False, classes=["table", "table-sm", "text-center"])))
