## Dividend Search

### Scratch Analysis

The first step is to perform the scratch analysis. This is the first filtering
and data analysis of stocks. Our main source of financial data is Yahoo Finance.

Inputs:
- A CSV file (;-separated) with the list of stocks to analyze. This is usually
all the stocks of an exchange, e.g., AMS. The CSV should contain at least a
column with the symbol of the stock and possible a friendly name.
- A comma-separated list of exchanges to search for the stock. This is a hint
for our source of financial data to locate the stock. The stock will be searched
in each of the given exchanges until found, or an error will be raised. If left
empty, no hint will be given.
- Output file name. This is the name that will be given to the resulting CSV
that will be created. A Dataframe will also be saved as pkt with the same name.

Output:
- The main output is the CSV with the analyzed data about dividend series, years
of dividend distributions and metrics such as ROE, Net Income margin, Debt, etc.
This prepares a dataset, showing the most interesting properties of the stocks
concerning dividends and health, which we can then furhter filter.

Example:

```bash
$ python3 scratch.py data/amsterdam_exch_2023-10-14.csv -e "AS,EPA" -o data/dividend_data_ams"
```


#### Read Data

The output of the scratch analysis can be passed to the `read_data` utility,
which will filter and render the result in HTML format.

**TODO: Explore whether this step can be easily replaced with a tool like Metabae, or other automation/data filtering**

Example:

```bash
$ python3 read_data.py data/dividend_data_ams > ams.html
```