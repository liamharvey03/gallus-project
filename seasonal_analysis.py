"""Quick seasonal analysis for Augie call — avg volume, pull-through, days-to-fund by calendar month."""
import sys
sys.path.insert(0, 'src')
from data_prep import load_and_clean
import pandas as pd
import numpy as np

df = load_and_clean()

# --- Funded loans only ---
funded = df[df['DidFund'] == 1].copy()
funded['fund_month'] = funded['Funded D'].dt.month
funded['fund_ym'] = funded['Funded D'].dt.to_period('M')

# --- Monthly funding volume (sum LoanAmount per calendar month instance) ---
monthly_vol = funded.groupby('fund_ym')['LoanAmount'].sum().reset_index()
monthly_vol.columns = ['period', 'volume']
monthly_vol['cal_month'] = monthly_vol['period'].dt.month
avg_vol = monthly_vol.groupby('cal_month')['volume'].mean()

# --- Pull-through rate by calendar month of loan open ---
df_resolved = df[df['Outcome'].isin(['Funded', 'Failed'])].copy()
df_resolved['open_month'] = df_resolved['Loan Open Date'].dt.month
pull_through = df_resolved.groupby('open_month')['DidFund'].mean()

# --- Avg days open to fund by funding calendar month ---
avg_days = funded.groupby('fund_month')['DaysTotalOpenToFund'].mean()

# --- Print table ---
months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

print()
print('=' * 75)
print('SEASONAL ANALYSIS: Monthly Averages Across All Years (2023-2025)')
print('=' * 75)
fmt = '{:<8} {:>14} {:>14} {:>18}'
print(fmt.format('Month', 'Avg Volume', 'Pull-Through', 'Avg Days to Fund'))
print('-' * 75)

for m in range(1, 13):
    vol = avg_vol.get(m, 0)
    pt = pull_through.get(m, 0)
    days = avg_days.get(m, 0)
    vol_str = '${:.1f}M'.format(vol / 1e6)
    pt_str = '{:.1%}'.format(pt)
    days_str = '{:.1f}'.format(days)
    print(fmt.format(months[m-1], vol_str, pt_str, days_str))

print('-' * 75)

# --- Summer vs Winter ---
summer = [5, 6, 7, 8]
winter = [11, 12, 1, 2]

summer_vol = avg_vol[[m for m in summer if m in avg_vol.index]].mean()
winter_vol = avg_vol[[m for m in winter if m in avg_vol.index]].mean()
summer_pt = pull_through[[m for m in summer if m in pull_through.index]].mean()
winter_pt = pull_through[[m for m in winter if m in pull_through.index]].mean()
summer_days = avg_days[[m for m in summer if m in avg_days.index]].mean()
winter_days = avg_days[[m for m in winter if m in avg_days.index]].mean()

print()
print('SUMMER (May-Aug) vs WINTER (Nov-Feb):')
diff_vol = (summer_vol / winter_vol - 1) * 100
print('  Avg Volume:     Summer ${:.1f}M  vs  Winter ${:.1f}M  ({:+.0f}%)'.format(
    summer_vol / 1e6, winter_vol / 1e6, diff_vol))
print('  Pull-Through:   Summer {:.1%}   vs  Winter {:.1%}'.format(summer_pt, winter_pt))
print('  Days to Fund:   Summer {:.1f}d     vs  Winter {:.1f}d'.format(summer_days, winter_days))

# --- Data depth ---
counts = monthly_vol.groupby('cal_month').size()
print()
print('Data depth (# of year-months per calendar month):')
parts = ['  {}:{}'.format(months[m-1], counts.get(m, 0)) for m in range(1, 13)]
print('  '.join(parts))
print()
