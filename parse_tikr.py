import pandas as pd
import numpy as np
from scipy import stats
import datetime
import jinja2 as j2

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
            s = s.replace(",","")
            if s.find("(") >= 0 and s.find(")") >= 0:
                s = s.replace("(","-").replace(")","")
            if s.find("%") >= 0:
                s = s.replace("%", "")
                s = float(s) / 100
    return s


def parse_table(t):
    t = t.set_index(t.columns[0])
    t = t.dropna(how='all').dropna(how='all', axis=1)
    t = t.drop([c for c in t.index if "YoY" in c])
    t = t.rename(columns=parse_date)
    t = t.applymap(lambda x:replacetonumbeR(x))
    t = t.astype(float)
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
        "ltm": series["LTM"],
    }
    if dispersion_metrics:
        metrics.update({
        "mean": series.mean(),
        "std": series.std(),
        "mean_z2": series[(np.abs(stats.zscore(series)) <= 2)].mean(),
        "std_z2": series[(np.abs(stats.zscore(series)) <= 2)].std()
    })
    return metrics


def get_income_stats(income: pd.DataFrame, years=5):
    result = {
        "revenues": get_series_stats(income.loc["Revenues"], dispersion_metrics=False, years=years),
        "gross": get_series_stats(income.loc["Gross Profit"], dispersion_metrics=False, years=years),
        "gross_margin": get_series_stats(income.loc["Gross Profit"] / income.loc["Revenues"], years=years),
        "gross_sga_margin": get_series_stats(-income.loc["Selling General & Admin Expenses"] / income.loc["Gross Profit"], years=years),
        "gross_depreciation_margin": get_series_stats(-income.loc["Depreciation & Amortization"] / income.loc["Gross Profit"] if "Depreciation & Amortization" in income.index else pd.Series(index=income.columns, dtype=int), years=years),
        "operating_income": get_series_stats(income.loc["Operating Income"], years=years, dispersion_metrics=False),
        "operating_margin": get_series_stats(income.loc["Operating Income"] / income.loc["Revenues"], years=years),
        "interest_expense_margin": get_series_stats(-income.loc["Interest Expense"] / income.loc["Operating Income"], years=years),
        "net_income": get_series_stats(income.loc["Net Income"], dispersion_metrics=False, years=years),
        "net_income_margin": get_series_stats(income.loc["Net Income"] / income.loc["Revenues"], years=years),
    }

    return result
    # return { ("%s_%s" % (k, vk)): result[k][vk] for k in result.keys() for vk in result[k].keys() }


def get_balance_stats(income: pd.DataFrame, balance: pd.DataFrame, years=5):
    result = {
        "cash": get_series_stats(balance.loc["Cash And Equivalents"], years=years),
        "inventory_margin": get_series_stats(balance.loc["Inventory"] / income.loc["Revenues"], years=years),
        "accounts_recv_margin": get_series_stats(balance.loc["Accounts Receivable"] / income.loc["Revenues"], years=years), # TIKR provides NET Accounts Receivables under this name
        "current_ratio": get_series_stats(balance.loc["Total Current Assets"] / balance.loc["Total Current Liabilities"], years=years),
        "goodwill": get_series_stats(balance.loc["Goodwill"], years=years),
        "assets": get_series_stats(balance.loc["Total Assets"], years=years),
        "roa": get_series_stats(income.loc["Net Income"] / balance.loc["Total Assets"], years=years),
        "net_debt": get_series_stats(balance.loc["Net Debt"], years=years),
        "debt_to_earnings": get_series_stats(balance.loc["Net Debt"] / income.loc["Net Income"], years=years),
        "debt_to_equity": get_series_stats(balance.loc["Net Debt"] / balance.loc["Total Equity"], years=years),
        "pref_shares": get_series_stats(balance.loc["Total Preferred Equity"] if "Total Preferred Equity" in balance.index else pd.Series(index=balance.columns, dtype=int), years=years),
        "retained_earnings": get_series_stats(balance.loc["Retained Earnings"], years=years, dispersion_metrics=False),
        "treasury_stock": get_series_stats(balance.loc["Treasury Stock"] if "Treasury Stock" in balance.index else pd.Series(index=balance.columns, dtype=int), years=years),
        "roe": get_series_stats(income.loc["Net Income"] / balance.loc["Total Equity"], years=years),
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


dfs = pd.read_html("data/tikr/Texas Roadhouse, Inc. (TXRH).html")

income = parse_table(dfs[0])
balance = parse_table(dfs[1])
cashflow = parse_table(dfs[2])

# table = pd.DataFrame.from_dict({'TXRH': get_income_stats(income)}, 'index')
income_table = pd.DataFrame(get_income_stats(income)).T
print(income_table.to_html(escape=False, formatters={ 'yy_growth': format_yy_growth_list, 'series': format_yy_growth_list } ))

balance_table = pd.DataFrame(get_balance_stats(income, balance)).T
print(balance_table.to_html(escape=False, formatters={ 'yy_growth': format_yy_growth_list, 'series': format_yy_growth_list } ))
