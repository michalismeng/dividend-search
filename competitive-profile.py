import pandas as pd
import numpy as np
from scipy import stats
import datetime
import jinja2 as j2
from os import listdir
from os.path import isfile, join
from pathlib import Path

import argparse

parser = argparse.ArgumentParser(
                    prog='Competitve Profile',
                    description='Produce HTML with processed financials from TIKR HTML full financials')
parser.add_argument("-f", "--folder", help="Input folder with the competitors HTML")
parser.add_argument("--format", default="html", nargs="?", choices=["html", "obsidian"], help="The output format. Default: html")

args = parser.parse_args()

j2_env = j2.Environment()

def parse_date(x):
    if x != "LTM":
        date = datetime.datetime.strptime(x, "%m/%d/%y")
        return str(date.year) + "-" + str(date.month)
    return x


def replacetonumbeR(s):
    if type(s).__name__ == "str":
        s = s.strip()
        if s == "-":
            s = 0
        else:
            s = s.replace("x", "")
            s = s.replace(",","")
            if s.find("(") >= 0 and s.find(")") >= 0:
                s = s.replace("(","-").replace(")","")
            if s.find("%") >= 0:
                s = s.replace("%", "")
                s = float(s) / 100
    return s


def parse_table(t):
    t = t.dropna(how='all')
    t = t.set_index(t.columns[0])
    t = t.dropna(how='all', axis=1)
    t = t.drop([c for c in t.index if "YoY" in c])
    t = t.rename(columns=parse_date)
    t = t.applymap(lambda x:replacetonumbeR(x))
    t = t.astype(float)
    t = t.fillna(0)
    return t


def get_growth_per_year(series, year):
    x = ((series.shift(-year) / series) ** (1 / year)) - 1
    x = x.dropna()
    return x.iloc[-1] if len(x) > 0 else np.NaN


def get_series_stats(series, years=5, dispersion_metrics=True):
    metrics = { 
        "series": list(series),
        "yy_growth": [get_growth_per_year(series, i) for i in range(years, 0, -1)],
        "yy_growth_5": get_growth_per_year(series, 5),
        "yy_growth_3": get_growth_per_year(series, 3),
        "yy_growth_1": get_growth_per_year(series, 1),
        "growth_tot": series.pct_change(periods=years).iloc[-1],
        "ltm": series["LTM"] if "LTM" in series else series.iloc[-1],
    }
    if dispersion_metrics:
        metrics.update({
        "mean": series.mean(),
        "std": series.std(),
        "mean_z2": series[(np.abs(stats.zscore(series)) <= 2)].mean(),
        "std_z2": series[(np.abs(stats.zscore(series)) <= 2)].std()
    })
    return metrics


def get_dividends(income):
    if "special dividends per share" in income.index:
        return income.loc["dividends per share"] + income.loc["special dividends per share"]
    else:
        return income.loc["dividends per share"]


def get_income_stats(income: pd.DataFrame, years=5):
    result = {
        "revenues": get_series_stats(income.loc["revenues"], dispersion_metrics=False, years=years),
        "gross": get_series_stats(income.loc["gross profit"], dispersion_metrics=False, years=years) if "gross profit" in income.index else np.NaN,
        "gross_margin": get_series_stats(income.loc["gross profit"] / income.loc["revenues"], years=years) if "gross profit" in income.index else np.NaN,
        "gross_sga_margin": get_series_stats(-income.loc["selling general & admin expenses"] / income.loc["gross profit"], years=years) if "gross profit" in income.index and "selling general & admin expenses" in income.index else np.NaN,
        "gross_depreciation_margin": get_series_stats(-income.loc["depreciation & amortization"] / income.loc["gross profit"], years=years) if "depreciation & amortization" in income.index else np.NaN,
        "gross_r&d_margin": get_series_stats(-income.loc["r&d expenses"] / income.loc["gross profit"], years=years) if "r&d expenses" in income.index else np.NaN,
        "operating_income": get_series_stats(income.loc["operating income"], years=years, dispersion_metrics=False),
        "operating_margin": get_series_stats(income.loc["operating income"] / income.loc["revenues"], years=years),
        "interest_expense_margin": get_series_stats(-income.loc["interest expense"] / income.loc["operating income"], years=years),
        "net_income": get_series_stats(income.loc["net income to common excl. extra items"], dispersion_metrics=False, years=years),
        "net_income_margin": get_series_stats(income.loc["net income to common excl. extra items"] / income.loc["revenues"], years=years),
        "diluted_shares": get_series_stats(income.loc["weighted average diluted shares outstanding"], years=years, dispersion_metrics=False),
        "eps": get_series_stats(income.loc["diluted eps excl extra items"], dispersion_metrics=False, years=years),
        "dividends": get_series_stats(get_dividends(income), years=years),
        "payout": get_series_stats(get_dividends(income), years=years),
        "missing_dividend_years": get_series_stats(pd.Series(((get_dividends(income) == 0)|(income.loc["dividends per share"].isna())).sum(), index=income.columns)),
    }

    return result
    # return { ("%s_%s" % (k, vk)): result[k][vk] for k in result.keys() for vk in result[k].keys() }


def get_balance_stats(income: pd.DataFrame, balance: pd.DataFrame, years=5):
    result = {
        "cash": get_series_stats(balance.loc["Cash And Equivalents"], years=years),
        "inventory_margin": get_series_stats(balance.loc["Inventory"] / income.loc["revenues"], years=years),
        "accounts_recv_margin": get_series_stats(balance.loc["Accounts Receivable"] / income.loc["revenues"], years=years), # TIKR provides NET Accounts Receivables under this name
        "current_ratio": get_series_stats(balance.loc["Total Current Assets"] / balance.loc["Total Current Liabilities"], years=years),
        "goodwill": get_series_stats(balance.loc["Goodwill"], years=years) if "Goodwill" in balance.index else np.NaN,
        "assets": get_series_stats(balance.loc["Total Assets"], years=years),
        "roa": get_series_stats(income.loc["net income to common excl. extra items"] / balance.loc["Total Assets"], years=years),
        "net_debt": get_series_stats(balance.loc["Net Debt"], years=years),
        "debt_to_earnings": get_series_stats(balance.loc["Net Debt"] / income.loc["net income"], years=years),
        "debt_to_equity": get_series_stats(balance.loc["Net Debt"] / balance.loc["Total Equity"], years=years),
        "pref_shares": get_series_stats(balance.loc["Total Preferred Equity"], years=years) if "Total Preferred Equity" in balance.index else np.NaN,
        "retained_earnings": get_series_stats(balance.loc["Retained Earnings"], years=years, dispersion_metrics=False),
        "treasury_stock": get_series_stats(balance.loc["Treasury Stock"], years=years) if "Treasury Stock" in balance.index else np.NaN,
        "roe": get_series_stats(income.loc["net income to common excl. extra items"] / balance.loc["Total Equity"], years=years),
    }

    return result


def get_cash_stats(income: pd.DataFrame, cash: pd.DataFrame, years=5):
    fcfe = cash.loc["Free Cash Flow"] + (cash.loc["Total Debt Issued"] + cash.loc["Total Debt Repaid"])
    result = {
        "operating_cashflow": get_series_stats(cash.loc["Cash from Operations"], years=years),
        "capital_intensity": get_series_stats(-cash.loc["Capital Expenditure"] / income.loc["net income"], years=years),
        "fcf": get_series_stats(cash.loc["Free Cash Flow"], years=years),
        "fcf_margins": get_series_stats(cash.loc["Free Cash Flow"] / income.loc["revenues"], years=years),
        "earnings_to_fcf": get_series_stats(income.loc["net income"] / cash.loc["Free Cash Flow"], years=years),
        "dividends_to_fcfe": get_series_stats(-cash.loc["Common Dividends Paid"] / fcfe, years=years),
        "buybacks_to_fcfe": get_series_stats(-cash.loc["Repurchase of Common Stock"] / fcfe, years=years),
        "d&b_to_fcfe": get_series_stats((-cash.loc["Repurchase of Common Stock"] - cash.loc["Common Dividends Paid"]) / fcfe, years=years)
    }

    return result


def format_yy_growth_list(yy_growth: list):
    template = """
    <div style="width: 100%; display: flex;">
    <svg viewBox="0 0 {{items * 4}} 20" width="40" style='margin: auto; padding: 5px'>
    {% for l in lst %}
        <path d="M{{loop.index0 * 4}} {{scaling}} h 2 v {{l / max_val * -scaling}} h -2"></path>
    {% endfor %}
    </svg>
    </div
    """
    template = j2_env.from_string(template)
    yy_growth_adjusted = [x if not np.isnan(x) else 0 for x in yy_growth]
    return template.render(lst=yy_growth_adjusted, items=len(yy_growth), max_val=np.max(np.abs(yy_growth_adjusted)), scaling=10 if any([x < 0 for x in yy_growth]) else 20)


def collapse_to_single(serie):
    return serie[(np.abs(stats.zscore(serie)) <= 2)].mean()

files = [join(args.folder, f) for f in listdir(args.folder) if isfile(join(args.folder, f))]

gross_margin_dict = {}
ebit_margin_dict = {}
interest_expense_margin_dict = {}
net_margin_dict = {}
levered_fcf_margin_dict = {}
debt_dict = {}
fcf_dict = {}
representatives = {}

for file in files:
    dfs = pd.read_html(file)

    income = parse_table(dfs[0])
    income.index = income.index.str.lower()
    # balance = parse_table(dfs[1])
    cashflow = parse_table(dfs[2])
    ratios = parse_table(dfs[3])
    columns = ratios.columns
    gross_margin_dict[Path(file).stem] = ratios.loc["Gross Profit Margin %"].tolist()
    ebit_margin_dict[Path(file).stem] = ratios.loc["EBIT Margin %"].tolist()
    net_margin_dict[Path(file).stem] = ratios.loc["Net Avail. For Common Margin %"].tolist()
    levered_fcf_margin_dict[Path(file).stem] = ratios.loc["Levered Free Cash Flow Margin %"].tolist()
    debt_dict[Path(file).stem] = ratios.loc["Net Debt / EBITDA"].tolist()
    interest_expense_margin_dict[Path(file).stem] = pd.Series(name="Interest Expense Margin %", data=(-income.loc["interest expense"] / income.loc["total revenues"])).tolist()
    fcf_dict[Path(file).stem] = cashflow.loc["Free Cash Flow"].tolist()


    rows = ["Gross Profit Margin %", "SG&A Margin %",
            lambda : pd.Series(name="R&D Margin %", data=(-income.loc["r&d expenses"] / income.loc["total revenues"])) if "r&d expenses" in income.index else pd.Series([], dtype=float, name="R&D Margin %"),
            "EBIT Margin %",
            lambda : pd.Series(name="Interest Expense Margin %", data=(-income.loc["interest expense"] / income.loc["total revenues"])),
            "Net Avail. For Common Margin %",
            "Levered Free Cash Flow Margin %",
            "Net Debt / EBITDA", "Return on Common Equity %", "Return On Equity %"]

    representatives[Path(file).stem] = ([get_growth_per_year(income.loc["total revenues"], len(income.columns) - 1)] +
                                        list(map(lambda x: collapse_to_single(x()) if callable(x) else collapse_to_single(ratios.loc[x]) if x in ratios.index else np.NaN, rows)))
    
metrics = {
    "gross-margin": {
        "title": "Gross Margins Comparison",
        "labels": columns.tolist(),
        "companies": gross_margin_dict
    },
    "ebit-margin": {
        "title": "Operating Margins Comparison",
        "labels": columns.tolist(),
        "companies": ebit_margin_dict
    },
    "interest-margin": {
        "title": "Interest Expense Margins Comparison",
        "labels": columns.tolist(),
        "companies": interest_expense_margin_dict
    },
    "net-margin": {
        "title": "Net Margins Comparison",
        "labels": columns.tolist(),
        "companies": net_margin_dict
    },
    "fcf-margin": {
        "title": "Levered FCF Margins Comparison",
        "labels": columns.tolist(),
        "companies": levered_fcf_margin_dict
    },
    "debt": {
        "title": "Net Debt / EBITDA",
        "labels": columns.tolist(),
        "companies": debt_dict
    },
    # "fcf": {
    #     "title": "FCF Comparison",
    #     "labels": columns.tolist(),
    #     "companies": fcf_dict
    # },
}

representatives = pd.DataFrame(representatives, index=(["Total Revenues (CAGR)"] + [r().name if callable(r) else r for r in rows])).T
for col in representatives.columns:
    if col == "Net Debt / EBITDA":
        representatives[col] = representatives[col].apply("{:.1f}x".format)
    else:
        representatives[col] = representatives[col].apply("{:.1%}".format)

if args.format == "html":
    with open("competitive-profile.html.j2") as f:
        template = j2_env.from_string(f.read())
        print(template.render(metrics=metrics, representatives=representatives.to_html(classes=["table", "table-sm", "table-hover", "text-center", "p-2"])))

if args.format == "obsidian":
    for key in metrics:
        metrics[key]["companies"] = pd.DataFrame(metrics[key]["companies"], index=columns).T.to_markdown()
    with open("competitive-profile.md.j2") as f:
        template = j2_env.from_string(f.read())
        print(template.render(metrics=metrics, representatives=representatives.to_markdown(), rdate=datetime.datetime.today().strftime('%Y-%m-%d')))
