import datetime
import pandas as pd
import requests
import streamlit as st

whoop_headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
    'Content-Type': 'application/json;charset=UTF-8',
}

def get_clean_whoop_data():

    response = get_whoop_response()
    df = get_dataframe(response)

    return df

def get_dataframe(response):
    rolling_window = '14D'
    new_years_day = datetime.date(2020, 12, 31)

    df = (
        pd.DataFrame(parse_response(response))
        .query('rem == rem')
        .assign(
            dt = lambda x: x['dt'].apply(lambda x: pd.to_datetime(x)),
            average_rhr = lambda x: x.rolling(rolling_window, on = 'dt')['resting_heart_rate'].mean().to_numpy(),
        )
        .query('dt >= @new_years_day')
    )

    return df

def get_whoop_response():

    whoop_headers.update({'authorization': f'bearer {get_access_token()}'})

    params = (
        ('end', f'{get_today()}T04:59:59.999Z'),
        ('start', '2020-06-21T05:00:00.000Z'),
    )

    response = requests.get(
        'https://api-7.whoop.com/users/340847/cycles',
        headers=whoop_headers,
        params=params
    )

    return response

def parse_response(response):

    parsed = []

    for element in response.json():
        dt = element['days'][0]
        whoop_id = element['id']
        sleeps = element['sleep']['sleeps']
        strain = element['strain']['score']
        if element['recovery']:
            rhv = element['recovery'].get('heartRateVariabilityRmssd')

            for sleep in sleeps:
                rem = sleep['remSleepDuration']
                deep = sleep['slowWaveSleepDuration']
                in_bed = sleep['inBedDuration']
                respiratory_rate = sleep['respiratoryRate']

                row = {
                    'dt': dt,
                    'whoop_id': whoop_id,
                    'rem': rem,
                    'deep': deep,
                    'strain': strain,
                    'rhv': rhv,
                    'in_bed': in_bed,
                    'resting_heart_rate': element['recovery']['restingHeartRate'],
                    'respiratory_rate': respiratory_rate,
                }
                parsed.append(row)

    return parsed

def get_today():
    return str(datetime.datetime.today().date())

def get_access_token():
    response = requests.post(
        'https://api-7.whoop.com/oauth/token',
        headers=whoop_headers,
        data=st.secrets['WHOOP_TOKEN_CREDENTIALS']
    )

    return response.json()['access_token']
