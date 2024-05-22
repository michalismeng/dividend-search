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
    df = df.drop(columns=["comment"])

cols = list(df.columns[0:list(df.columns).index("Outliers")]) + list(df.columns[list(df.columns).index("Outliers") + 1:]) + ["Outliers"]
df = df[cols]
df = df.sort_values(by="Symbol")

with open("template.html.j2") as f:
    template = j2_env.from_string(f.read())
print(template.render(table=df
                              .set_axis(range(1, len(df)+1))
                              .to_html(index=True, classes=["table", "table-sm", "table-hover", "text-center", "text-nowrap"], formatters={
    'Growth Tot': '{:,.2%}'.format,
    'Growth Y/Y': '{:,.2%}'.format,
    'Growth 3Y/Y': '{:,.2%}'.format,
    'Growth 5Y/Y': '{:,.2%}'.format,
    'Growth 1Y/Y': '{:,.2%}'.format,
    'Years': '{:.0f}'.format,
    'Missing Years': '{:.0f}'.format,
    'Net Margin': '{:,.2%}'.format,
    'Debt Ratio': '{:,.2}'.format,
    'ROE': '{:,.2%}'.format,
    'Current Ratio': '{:,.2}'.format,
    'Share Growth 3Y/Y': '{:,.2%}'.format,
    'CapEx Ratio': '{:,.2%}'.format,
})).replace("text-align: right", ""))
