from bs4 import BeautifulSoup
import datetime
from dataclasses import dataclass
import json
import pandas as pd
import requests
import streamlit as st

withings_headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
    'Referer': 'https://healthmate.withings.com/',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-site',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36',
    'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="100", "Google Chrome";v="100"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"macOS"',
}

@dataclass
class BundledData:
    session_cookies: json = None
    response: json = None
    email: str = st.secrets['WITHINGS_EMAIL'].replace('@', '%40')
    password: str = st.secrets['WITHINGS_PASSWORD']

def get_clean_withings_data():
    bundle = BundledData()
    bundle.session_cookies = get_session_cookies(bundle)
    bundle.response = get_response(bundle)

    df = get_clean_data(bundle)

    return df

def get_clean_data(bundle):

    rolling_window = '14D'
    new_years_day = datetime.date(2020, 12, 31)

    df = (
        parse_response(bundle)
        .query('type.isin([1, 6])')
        .pivot_table(
            index=['dt', 'timestamp'],
            columns = 'type',
            values='value'
        )
        .reset_index()
        .set_axis(['dt', 'timestamp', 'grams', 'raw_body_fat'], axis=1,inplace=False)
        .query('raw_body_fat == raw_body_fat')
        .query('raw_body_fat > 18000')
        .query('raw_body_fat < 26400')
        .assign(
            dt_mon = lambda x: x['dt'].apply(lambda x: x.replace(day=1)),
            dt = lambda x: x['dt'].apply(lambda x: pd.to_datetime(x)),
            end_of_month = lambda x: x.groupby('dt_mon')['timestamp'].rank(ascending=False),
            lbs = lambda x: x['grams']/454,
            body_fat = lambda x: x['raw_body_fat']/1000,
            average_body_fat = lambda x: x.rolling(rolling_window, on = 'dt')['body_fat'].mean().to_numpy(),
            average_weight = lambda x: x.rolling(rolling_window, on = 'dt')['lbs'].mean().to_numpy(),
            )
        .query('dt >= @new_years_day')
    )

    return df

def parse_response(bundle):
    data = bundle.response.json()['body']['measuregrps']

    withings = []

    for element in data:
        timestamp = element['date']
        dt = datetime.datetime.utcfromtimestamp(timestamp).date()

        for measure in element['measures']:
            row = {
                'dt': dt,
                'timestamp': timestamp,
                'type': measure['type'],
                'value': measure['value']
            }
            withings.append(row)

    parsed_response = pd.DataFrame(withings)

    return parsed_response

def get_response(bundle):

    cookies = {

        'email': bundle.email,
        'session_key': bundle.session_cookies['session_key'],
        'session_token': bundle.session_cookies['session_token'],

    }

    data = {
        'action': 'getmeas',
        'userid': '23092328',
        'startdate': '1577854800',
        'enddate': get_current_timestamp(),
        'appname': 'hmw',
        'apppfm': 'web',
        'appliver': '54591b62',
        'session_token': bundle.session_cookies['session_token'],
    }

    response = requests.post('https://scalews.withings.com/cgi-bin/measure', headers=withings_headers, data=data, cookies=cookies)

    return response

def get_csrf_token():
    response = requests.get(
        'https://account.withings.com/connectionwou/account_login?r=https://healthmate.withings.com/',
        headers=withings_headers
    )

    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_token = soup.find('input', attrs={'name': 'csrf_token'})['value']

    return csrf_token

def get_session_cookies(bundle):

    cookies = {
        'email': bundle.email,
    }


    params = {
        'r': 'https://account.withings.com/connectionwou/account_login?r=https://healthmate.withings.com/?r=https://healthmate.withings.com/',
    }

    data = {
        'csrf_token': get_csrf_token(),
        'password': bundle.password,
    }

    session = requests.Session()

    response = session.post('https://account.withings.com/new_workflow/password_check', params=params, cookies=cookies, headers=withings_headers, data=data)

    session_cookies = session.cookies.get_dict()

    return session_cookies

def get_current_timestamp():
    return str(int(datetime.datetime.now().timestamp()))
