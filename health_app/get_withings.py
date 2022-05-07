import datetime
import pandas as pd
import requests
import streamlit as st
import time

def get_withings_response():
    payload_data = f'action=getmeas&userid=23092328&startdate=1548997200&enddate={current_unix_timestamp()}&appname=hmw&apppfm=web&appliver=761558a26aff821c9ec7fd86e00b999fc0139dad'

    cookies = {
        'session_key': get_withings_session_key(),
    }

    response = requests.post(
        'https://scalews.withings.com/cgi-bin/measure',
        cookies=cookies,
        data=payload_data)

    return response

def get_withings_session_key():
    params = (
        ('r', 'https://healthmate.withings.com/'),
    )

    data = {
      'email': st.secrets['WITHINGS_EMAIL'],
      'password': st.secrets['WITHINGS_PASSWORD'],
      'use_2fa': '',
      'is_admin': 'f',
      'advanced_login_token': '',
      'path_params_to_add': '[]'
    }

    session = requests.Session()
    response = session.post('https://account.withings.com/connectionwou/account_login', params=params, data=data)
    session_key = session.cookies.get_dict()['session_key']

    return session_key

def current_unix_timestamp():
    return int(time.time())

def get_withings_data_raw():
    data = get_withings_response().json()['body']['measuregrps']

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

    return pd.DataFrame(withings)


def get_clean_withings_data():
    rolling_window = '14D'
    new_years_day = datetime.date(2020, 12, 31)

    df = (
        get_withings_data_raw()
        .query('type.isin([1, 6])')
        .pivot_table(
            index=['dt', 'timestamp'],
            columns = 'type',
            values='value'
        )\
        .reset_index()\
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
            )\
        .query('dt >= @new_years_day')
    )

    return df
