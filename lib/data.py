from bs4 import BeautifulSoup
import numpy as np
import pandas as pd
import random
import re
import requests
import time
import xmltodict

from lib.cfg import *

# get company/cik level filing metadata
def get_acc_no(str_description):
    str_acc_no = re.search('Acc-no: (.*)\xa0', str_description)
    str_acc_no = str_acc_no.group(1).split('\xa0')[0].replace('-', '')
    
    return str_acc_no


def get_13F_QR_XML_url(cik, acc_no):
    url = URL_13F_QR_XML
    cik = str(int(cik))
    url = url.replace('[cik]', cik).replace('[acc_no]', acc_no)

    return url


def get_13f_metadata_table(cik:str):
    url = URL_COMPANY_FILING_SEARCH.replace('[cik]', cik)
    r = requests.get(url)
    byte_html_cik_search = r.content
    str_html_cik_search = byte_html_cik_search.decode("utf-8") 

    # extract table from cik search
    soup = BeautifulSoup(str_html_cik_search, 'lxml') # Parse the HTML as a string
    table = soup.find_all('table')[2] # The thrid table is data table

    dict_table = {}
    cols = list(map(lambda x: x.text, table.select('th')))

    for i, col in enumerate(cols):
        dict_table[col] = list(map(lambda x: x.text, table.select('td')[i::5]))

    df_table = pd.DataFrame(dict_table)
    df_table['cik'] = cik
    df_13f_metadata = df_table[df_table['Filings'] == '13F-HR'].copy()

    # calculate acc_no
    df_13f_metadata['acc_no'] = df_13f_metadata['Description'].apply(get_acc_no)

    # calculate 13F QR XML URL
    list_urls = []
    for i, row in df_13f_metadata.iterrows():
        url = get_13F_QR_XML_url(row['cik'], row['acc_no'])
        list_urls.append(url)

    df_13f_metadata['xml_url'] = list_urls
    df_13f_metadata = df_13f_metadata[[
        'cik', 
        'acc_no', 
        'Filings',
        'Filing Date', 
        'Format', 
        'Description', 
        'File/Film Number', 
        'xml_url'
    ]]

    df_13f_metadata = df_13f_metadata.rename(
        {
            'Filings': 'filings',
            'Filing Date': 'filing_date', 
            'Format': 'format', 
            'Description': 'description',
            'File/Film Number': 'file_number'
        }, 
        axis=1
    )
    
    return df_13f_metadata


# get filing info
def get_13f_holdings_table(cik, acc_no, filing_date, url):
    # Get XML table
    r = requests.get(url)
    byte_xml = r.content
    str_xml = byte_xml.decode("utf-8") 

    # Parse XML table
    dict_informationTable = xmltodict.parse(str_xml)
    df_13f_holdings = pd.DataFrame(dict_informationTable['informationTable']['infoTable'])
    df_13f_holdings['cik'] = cik
    df_13f_holdings['acc_no'] = acc_no
    df_13f_holdings['filing_date'] = filing_date

    # Formatting column subgroup
    df_13f_holdings['sshPrnamt'] = df_13f_holdings.apply(lambda x: x['shrsOrPrnAmt']['sshPrnamt'], axis=1)
    df_13f_holdings['sshPrnamtType'] = df_13f_holdings.apply(lambda x: x['shrsOrPrnAmt']['sshPrnamtType'], axis=1)
    df_13f_holdings = df_13f_holdings.drop(['shrsOrPrnAmt'], axis=1)

    df_13f_holdings['votingAuthority'] = df_13f_holdings.apply(lambda x: x['votingAuthority']['Sole'], axis=1)
    df_13f_holdings = df_13f_holdings.drop(['votingAuthority'], axis=1)
    
    # Formatting column names
    df_13f_holdings = df_13f_holdings.rename(
        {
            'nameOfIssuer': 'name_of_issuer',
            'titleOfClass': 'title_of_class', 
            'putCall': 'put_call',
            'sshPrnamt': 'ssh_prn_amt', 
            'sshPrnamtType': 'ssh_prn_amt_type',
            'investmentDiscretion': 'investment_discretion',
            'otherManager': 'other_manager'
        }, 
        axis=1
    )
    
    return df_13f_holdings


def map_filing_date_to_quarter(filing_date):
    # Form 13F quarterly filing is due for Q1 2020 within 45 days after the end of the calendar quarter. Due date is May 15, 2020
    quarter_mapping = {
        1: 4,
        2: 1,
        3: 2,
        4: 3,
    }
    
    year = filing_date.split('-')[0]
    quarter = pd.Timestamp(filing_date).quarter
    filing_quarter = year + '-Q' + str(quarter_mapping[quarter])
    
    return filing_quarter


def get_lastest_n_filings(df_13f_metadata, n):
    df_13f_holdings_agg = pd.DataFrame(
        columns= [
            'cik',
            'acc_no', 
            'filing_date', 
            'name_of_issuer',
            'title_of_class',
            'cusip', 
            'value', 
            'put_call', 
            'ssh_prn_amt', 
            'ssh_prn_amt_type', 
            'investment_discretion', 
            'other_manager'
        ]
    )

    for i in range(n):
        row = df_13f_metadata.iloc[i]
        df_13f_holdings = get_13f_holdings_table(row['cik'], row['acc_no'], row['filing_date'], row['xml_url'])
        df_13f_holdings_agg = df_13f_holdings_agg.append(df_13f_holdings)

        # random sleep 1~10 sec
        random_sleep = 1 + random.random()*9
        print('random sleep: ', random_sleep, ' second')
        time.sleep(random_sleep)

    df_13f_holdings_agg.reset_index(drop=True, inplace=True)
    df_13f_holdings_agg['filing_quarter'] = df_13f_holdings_agg['filing_date'].apply(map_filing_date_to_quarter)
    
    return df_13f_holdings_agg

