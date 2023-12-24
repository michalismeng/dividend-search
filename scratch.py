import yfinance as yf
import pandas as pd
import numpy as np
from scipy import stats
import datetime
import pytz
import argparse

parser = argparse.ArgumentParser(
                    prog='scratch',
                    description='Create list of companies paying dividends along with metrics of their financial health')
parser.add_argument("filename", help="CSV file of symbols of companies to perform the search. The file should be ';' separated")
parser.add_argument("-e", "--exchanges", default="", help="A comma-separated list of the exchanges to search for the stock. If left empty, the symbol will be search at the most common.")
parser.add_argument("-o", "--output", metavar="FILENAME", required=True)

args = parser.parse_args()

class DividendException(Exception):
    pass

def get_dividend_stats(symbol, div_df, years_of_analysis=10):
    if years_of_analysis < 5:
        raise DividendException("We only do analysis of 5 or more years")
    tz = pytz.timezone(str(div_df["Date"].iloc[0].tz))

    start_year = datetime.date.today().year - years_of_analysis
    div_df_10yrs = div_df[div_df["Date"] >= datetime.datetime(start_year - 1, 12, 31, tzinfo=tz)]
    div_df_10yrs_grouped = div_df_10yrs.groupby(div_df_10yrs["Date"].dt.year).sum(numeric_only=True).reset_index()
    if len(div_df_10yrs_grouped) <= 5:
        raise DividendException({ "symbol": symbol, "error": "Too few dividends" })

    all_years = pd.Series(range(div_df_10yrs_grouped["Date"].min(), div_df_10yrs_grouped["Date"].max() + 1))

    year_10 = 10 if len(div_df_10yrs_grouped) > 10 else len(div_df_10yrs_grouped) - 1
    missing_dividend_years = all_years[all_years.isin(div_df_10yrs_grouped["Date"]) == False]

    return {
        "symbol": symbol,
        "growth_tot": div_df_10yrs_grouped["Dividends"].pct_change(periods=year_10).iloc[-1],
        "growth_yy": get_growth_per_year(div_df_10yrs_grouped["Dividends"], year_10),
        "growth_yy_5": get_growth_per_year(div_df_10yrs_grouped["Dividends"], 5),
        "growth_yy_3": get_growth_per_year(div_df_10yrs_grouped["Dividends"], 3),
        "growth_yy_1": get_growth_per_year(div_df_10yrs_grouped["Dividends"], 1),
        "years": year_10,
        "missing_dividend_years_cnt": missing_dividend_years.count(),
        "outliers": div_df_10yrs_grouped[(np.abs(stats.zscore(div_df_10yrs_grouped["Dividends"])) > 2)].to_dict(orient="records"),
    }


def get_growth_per_year(series, year):
    x = ((series.shift(-year) / series) ** (1 / year)) - 1
    return x.dropna().iloc[-1]


def get_ticker_from_symbol(symbol, exchanges):
    if exchanges:
        exch = exchanges[0]
        company = yf.Ticker(symbol + ".%s" % exch)
    else:
        company = yf.Ticker(symbol)
    div_df = pd.DataFrame(company.dividends)
    if len(div_df) >= 6:
        return company
    elif len(div_df) == 0 and len(exchanges) - 1 > 0:
        return get_ticker_from_symbol(symbol, exchanges[1:])
    raise DividendException({ "symbol": symbol + ".%s" % exch, "error": "Too few dividends" })


def get_net_debt(balance):
    if "Net Debt" in balance.index and not pd.isna(balance.loc["Net Debt"]):
        return balance.loc["Net Debt"]
    elif "Total Debt" in balance.index and "Cash Cash Equivalents And Short Term Investments" in balance.index:
        return balance.loc["Total Debt"] - balance.loc["Cash Cash Equivalents And Short Term Investments"]
    elif "Total Debt" in balance.index and "Cash And Cash Equivalents" in balance.index:
        return balance.loc["Total Debt"] - balance.loc["Cash And Cash Equivalents"]
    return np.NaN 


def get_trimmed_mean(series, t=0.02):
    """ Return the trimmed mean over the given series.
    """
    qlow = series.quantile(t)
    qhigh = series.quantile(1 - t)
    return series[(series >= qlow) & (series <= qhigh)].mean()


def get_net_income_margins_mean(income, t=0.02):
    if any(income.loc["Total Revenue"] == 0):
        return np.NaN
    x = income.loc["Net Income"] / income.loc["Total Revenue"]
    return get_trimmed_mean(x, t)


def parse_stock(symbol, exchanges):
    company = get_ticker_from_symbol(symbol, exchanges)
    div_df = pd.DataFrame(company.dividends).reset_index().sort_values(by="Date")
    result = get_dividend_stats(company.ticker, div_df)

    balance = company.balance_sheet.sort_index(axis=1)
    income = company.income_stmt.sort_index(axis=1)
    cash = company.cash_flow.sort_index(axis=1)

    if not len(balance) or not len(income) or not len(cash):
        return result

    latest = balance.columns.sort_values()[-1]
    result["Net Margin"] = get_net_income_margins_mean(income)
    result["Debt Ratio"] = get_net_debt(balance[latest]) / get_trimmed_mean(income.loc["Net Income"])
    result["ROE"] = get_trimmed_mean(income.loc["Net Income"]) / balance[latest].loc["Stockholders Equity"]
    result["Current Ratio"] = balance[latest].loc["Current Assets"] / balance[latest].loc["Current Liabilities"] if "Current Assets" in balance.index and "Current Liabilities" in balance.index else np.NaN
    result["Share Growth 3Y/Y"] = get_growth_per_year(income.loc["Diluted Average Shares"], -3) if "Diluted Average Shares" in income.index and len(income.loc["Diluted Average Shares"].dropna()) == 4 else np.NaN
    result["CapEx Ratio"] = -cash.loc["Capital Expenditure"].sum() / income.loc["Net Income"].sum() if "Capital Expenditure" in cash.index else np.NaN
    try:
        result["Sector"] = "%s - %s" % (company.info["sector"], company.info["industry"])
    except Exception:
        result["Sector"] = ""

    return result

datas = []
stocks = pd.read_csv(args.filename, sep=";")
print("Found %s symbols" % len(stocks))
if "Name" not in stocks:
    stocks["Name"] = stocks["Symbol"]

exchanges = list(filter(lambda x: len(x), [e.strip() for e in args.exchanges.split(",")]))

for index, stock in stocks.iterrows():
    print("Retrieving dividend data for:", stock["Name"], "(%s)" % stock["Symbol"])
    try:
        data = parse_stock(stock["Symbol"], exchanges=exchanges)
        datas.append({ **data, "comment": "ok" })
    except DividendException as e:
        datas.append({ "symbol": e.args[0]["symbol"], "comment": e.args[0]["error"] })
    except Exception as e:
        print("Could not process symbol %s" % stock["Symbol"])
        datas.append({ "symbol": stock["Symbol"], "comment": "Exception when parsing" })

df = pd.DataFrame(datas)
df.to_csv("%s.csv" % args.output, index=False)
df.to_parquet("%s.pkt" % args.output)

# benchmark = ["KO", "MCO", "SPGI", "UNP", "WFC", "PEP", "BUD", "TAP", "KHC", "PM", "AXP", "WMT"]
# anti_benchmark = ["GM", "PG", "UAL", "AAL", "GT"]

# datas = []
# for stock in benchmark + anti_benchmark:
#     print("Retrieving dividend data for:", stock)
#     try:
#         data = parse_stock(stock)
#         datas.append({ **data, "comment": "ok" })
#     except Exception as e:
#         datas.append({ "symbol": e.args[0]["symbol"], "comment": e.args[0]["error"] })

#     print()

# df = pd.DataFrame(datas)
# df.to_csv("benchmark_dividend_data.csv")
# df.to_parquet("benchmark_dividend_data.pkt")