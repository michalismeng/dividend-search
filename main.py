import yfinance as yf
import pandas as pd
import numpy as np
from scipy import stats
import datetime
import pytz

ams_stocks = pd.read_csv("amsterdam_exch_2023-10-14.csv", sep=";")

def get_dividend_stats(symbol, div_df):
    tz = pytz.timezone(str(div_df["Date"].iloc[0].tz))
    div_df_10yrs = div_df[div_df["Date"] >= datetime.datetime(2013, 1, 1, tzinfo=tz)]
    div_df_10yrs_grouped = div_df_10yrs.groupby(div_df_10yrs["Date"].dt.year).sum(numeric_only=True).reset_index()
    if len(div_df_10yrs_grouped) < 3:
        raise Exception({ "symbol": symbol, "error": "Too few dividends in past 10 years" })
    year_10 = 10 if len(div_df_10yrs_grouped) > 10 else len(div_df_10yrs_grouped) - 1
    year_5 = 5 if len(div_df_10yrs_grouped) > 5 else len(div_df_10yrs_grouped) - 1

    return {
        "symbol": symbol,
        "growth_10": div_df_10yrs_grouped["Dividends"].pct_change(periods=year_10).iloc[-1],
        "growth_yy_10": ((div_df_10yrs_grouped["Dividends"].shift(-year_10) / div_df_10yrs_grouped["Dividends"]) ** (1 / year_10) - 1).dropna().iloc[-1],
        "growth_yy_5": ((div_df_10yrs_grouped["Dividends"].shift(-year_5) / div_df_10yrs_grouped["Dividends"]) ** (1 / year_5) - 1).dropna().iloc[-1],
        "growth_yy_2": ((div_df_10yrs_grouped["Dividends"].shift(-2) / div_df_10yrs_grouped["Dividends"]) ** (1 / 2) - 1).dropna().iloc[-1],
        "growth_yy_1": ((div_df_10yrs_grouped["Dividends"].shift(-1) / div_df_10yrs_grouped["Dividends"]) ** (1 / 1) - 1).dropna().iloc[-1],
        "growth_med": div_df_10yrs_grouped["Dividends"].pct_change(periods=1).median(),
        "outliers": div_df_10yrs_grouped[(np.abs(stats.zscore(div_df_10yrs_grouped["Dividends"])) > 2)].to_dict(orient="records"),
        "years_10": year_10,
        "years_5": year_5 
    }

def get_ticker_from_symbol(symbol):
    exch = "AS"
    company = yf.Ticker(symbol + ".%s" % exch)
    div_df = pd.DataFrame(company.dividends).reset_index()
    if len(div_df) > 3:
        return company
    elif len(div_df) == 0:
        exch = "PA"
        company = yf.Ticker(symbol + ".%s" % exch)
        div_df = pd.DataFrame(company.dividends).reset_index()
        if len(div_df) > 3:
            return company
        elif len(div_df) == 0:
            exch = "BR"
            company = yf.Ticker(symbol + ".%s" % exch)
            div_df = pd.DataFrame(company.dividends).reset_index()
            if len(div_df) > 3:
                return company
    raise Exception({ "symbol": symbol + ".%s" % exch, "error": "Too few dividends" })

def parse_stock(symbol):
    company = get_ticker_from_symbol(symbol)
    div_df = pd.DataFrame(company.dividends).reset_index()
    result = get_dividend_stats(company.ticker, div_df)

    balance = company.balance_sheet
    income = company.income_stmt
    latest = balance.columns.sort_values()[-1]
    result["Net Debt / Net Income Med"] = balance[latest]["Net Debt"] / income.loc["Net Income"].median()

    return result

datas = []
for index, stock in ams_stocks[:10].iterrows():
    print("Retrieving dividend data for:", stock["Name"], "(%s)" % stock["Symbol"])
    try:
        data = parse_stock(stock["Symbol"])
        datas.append({ **data, "comment": "ok" })
    except Exception as e:
        datas.append({ "symbol": e.args[0]["symbol"], "comment": e.args[0]["error"] })

    print()

df = pd.DataFrame(datas)
df.to_csv("dividend_data.csv")
df.to_parquet("dividend_data.pkt")
# print(parse_stock(ams_stocks.iloc[0]["Symbol"]))
