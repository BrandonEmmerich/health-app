import altair as alt
import pandas as pd
import streamlit as st

import get_withings

@st.cache(ttl=3600)
def fetch_and_clean_data():
    df = get_withings.get_clean_withings_data()
    return df

df = fetch_and_clean_data()

average_body_fat = round(df.tail(1)['average_body_fat'].tolist()[0],1)
average_weight = round(df.tail(1)['average_weight'].tolist()[0],1)

st.write(
f"""
# Brandon's Fitness Metrics

### Weight: {average_weight} lbs
"""
)

weight = (
    alt
    .Chart(df)
    .mark_line()
    .encode(
        alt.Y(
            'average_weight',
            scale=alt.Scale(zero=False),
            axis=alt.Axis(title='Average Weight\n(lbs)')
        ),
        alt.X(
            'dt',
            axis=alt.Axis(title='')
        ),
        tooltip=['dt', 'average_weight']
    )
    .interactive()
)

body_fat = (
    alt
    .Chart(df)
    .mark_line()
    .encode(
        alt.Y(
            'average_body_fat',
            scale=alt.Scale(zero=False),
            axis=alt.Axis(title='Average Body Fat\n(%)')
        ),
        alt.X(
            'dt',
            axis=alt.Axis(title='')
        ),
        tooltip=['dt', 'average_body_fat']
    )
    .interactive()
)

st.altair_chart(weight, use_container_width=True)

st.write(
f"""
### Body Fat Percentage: {average_body_fat}%
"""
)

st.altair_chart(body_fat, use_container_width=True)

body_composition_data = (
    df
     .query('end_of_month == 1')
    [['dt_mon', 'average_body_fat', 'average_weight']]
    .assign(
        fat_pounds = lambda x: x['average_weight'] * x['average_body_fat'] / 100
    )
    .round(2)
    .assign(
        Fat = lambda x: x['fat_pounds'] - x ['fat_pounds'].shift(1),
        delta_pounds = lambda x: x['average_weight'] - x['average_weight'].shift(1),
        Muscle = lambda x: round(x['delta_pounds'] - x['Fat'],2)
    )
    .melt(
        id_vars='dt_mon',
        value_vars=['Fat', 'Muscle'],
        var_name='Body Composition'
    )
)

body_comp = alt.Chart(body_composition_data).mark_bar(size=20).encode(
    alt.X(
        'dt_mon',
        axis=alt.Axis(title='')
    ),
    alt.Y(
        'value',
        axis=alt.Axis(title='Body Composition Change\n(lbs)')
    ),
    color='Body Composition',
    tooltip=['dt_mon', 'value', 'Body Composition']
).interactive()

st.write(
f"""
### Body Composition Changes
"""
)

st.altair_chart(body_comp, use_container_width=True)

st.write(
"""
\*More to come....
"""
)
