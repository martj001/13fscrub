from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


class HoldingAnalyzer():
    def __init__(self, df_holdings, quarter_start, quarter_end):
        self.df_holdings = df_holdings
        self.quarter_start = quarter_start
        self.quarter_end = quarter_end
        
        self.preproc()
    
    def preproc(self):
        df_holdings = self.df_holdings
        
        df_holdings = df_holdings.drop(['cik', 'acc_no', 'filing_date', 'investment_discretion', 'other_manager'], axis=1)
        df_holdings[['value', 'ssh_prn_amt']] = df_holdings[['value', 'ssh_prn_amt']].astype(int)
        self.df_holdings_start = df_holdings[df_holdings['filing_quarter'] == self.quarter_start]
        self.df_holdings_end = df_holdings[df_holdings['filing_quarter'] == self.quarter_end]
        
        self.df_holdings = df_holdings
        
    def get_holdings_added(self):
        cusip_added = set(self.df_holdings_end['cusip']) - set(self.df_holdings_start['cusip'])
        df_holdings_added = pd.DataFrame({'cusip': list(cusip_added)}).merge(self.df_holdings_end).sort_values('name_of_issuer')
        
        return df_holdings_added
        
    def get_holdings_removed(self):
        cusip_removed = set(self.df_holdings_start['cusip']) - set(self.df_holdings_end['cusip'])
        df_holdings_removed = pd.DataFrame({'cusip': list(cusip_removed)}).merge(self.df_holdings_start).sort_values('name_of_issuer')
        
        return df_holdings_removed
        
    def get_holdings_changed(self):
        cusip_coexist = set.intersection(set(self.df_holdings_end['cusip']), set(self.df_holdings_start['cusip']))
        df_holdings_coexist_start = pd.DataFrame({'cusip': list(cusip_coexist)}).merge(self.df_holdings_start)
        df_holdings_coexist_end = pd.DataFrame({'cusip': list(cusip_coexist)}).merge(self.df_holdings_end)

        df_holdings_coexist_start = df_holdings_coexist_start[['name_of_issuer', 'cusip', 'put_call', 'ssh_prn_amt', 'value']]
        df_holdings_coexist_start = df_holdings_coexist_start.rename({'ssh_prn_amt': 'shares_start', 'value': 'value_start'}, axis=1)
        df_holdings_coexist_end = df_holdings_coexist_end[['name_of_issuer', 'cusip', 'put_call', 'ssh_prn_amt', 'value']]
        df_holdings_coexist_end = df_holdings_coexist_end.rename({'ssh_prn_amt': 'shares_end', 'value': 'value_end'}, axis=1)

        df_holdings_coexist = df_holdings_coexist_start.merge(df_holdings_coexist_end, on=['name_of_issuer', 'cusip', 'put_call'], how='outer')
        df_holdings_coexist.sort_values(['name_of_issuer'], inplace=True)
        df_holdings_coexist = df_holdings_coexist.fillna(0)

        df_holdings_coexist['shares_delta'] = df_holdings_coexist['shares_end'] - df_holdings_coexist['shares_start']
        df_holdings_coexist['value_delta'] = df_holdings_coexist['value_end'] - df_holdings_coexist['value_start']

        df_holdings_coexist = df_holdings_coexist[[
            'name_of_issuer', 'cusip', 'put_call', 
            'shares_start', 'shares_end', 'shares_delta', 
            'value_start', 'value_end', 'value_delta'
        ]]
        
        return df_holdings_coexist
        
    def get_holdings_pie(self):
        df_holdings_start_pie = self.df_holdings_start[['name_of_issuer', 'value']].groupby(['name_of_issuer']).agg(sum)
        df_holdings_start_pie = df_holdings_start_pie.reset_index().sort_values(['value'])
        df_holdings_end_pie = self.df_holdings_end[['name_of_issuer', 'value']].groupby(['name_of_issuer']).agg(sum)
        df_holdings_end_pie = df_holdings_end_pie.reset_index().sort_values(['value'])
        
        sns.set_style('whitegrid')

        portfolio_value_start = sum(df_holdings_start_pie['value'])
        portfolio_value_end = sum(df_holdings_end_pie['value'])
        portfolio_growth = np.round((portfolio_value_end/portfolio_value_start), 1)

        fig = plt.figure(figsize=[20,10])
        ax = fig.add_subplot(121)
        ax.pie(
            df_holdings_start_pie['value'],
            labels=df_holdings_start_pie['name_of_issuer']
        )
        ax.set_title('Portfolio Value: ' + str(portfolio_value_start) + ' | ' + str(1.0) + 'x')

        ax = fig.add_subplot(122)
        ax.pie(
            df_holdings_end_pie['value'],
            labels=df_holdings_end_pie['name_of_issuer']
        )
        ax.set_title('Portfolio Value: ' + str(portfolio_value_end) + ' | ' + str(portfolio_growth) + 'x')
        plt.show()
        
