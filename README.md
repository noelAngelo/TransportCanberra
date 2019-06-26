

```python
from pandas.io.json import json_normalize
from sodapy import Socrata
from elasticsearch import Elasticsearch

import plotly.plotly as py
import plotly.graph_objs as go
from plotly.offline import download_plotlyjs, init_notebook_mode, plot, iplot
init_notebook_mode(connected=True)
import json
import requests
import numpy as np
import pandas as pd
import datetime
from datetime import timedelta 
import os, time
import pytz
import arrow
import qgrid
```


<script type="text/javascript">window.PlotlyConfig = {MathJaxConfig: 'local'};</script><script type="text/javascript">if (window.MathJax) {MathJax.Hub.Config({SVG: {font: "STIX-Web"}});}</script><script>requirejs.config({paths: { 'plotly': ['https://cdn.plot.ly/plotly-latest.min']},});if(!window._Plotly) {require(['plotly'],function(plotly) {window._Plotly=plotly;});}</script>



```python
# get credentials
with open('.credentials') as f:
    credentials = f.readlines()
    credentials = json.loads(''.join(credentials).strip())
```

# Helper Functions


```python
# adds information from trips.csv and stops.csv
def CSDM(dff, trips, stops):
    
    # convert columns to datetime and int
    dff['arrival_delay'] = dff['arrival_delay'].astype(int)
    dff['depature_delay'] = dff['depature_delay'].astype(int)
    dff['stop_sequence'] = dff['stop_sequence'].astype(int)
    
    trips['trip_id'] = trips['trip_id'].astype(str)
    stops['stop_id'] = stops['stop_id'].astype(str)
    
    dff['arrival_time'] = dff['arrival_time'].apply(lambda x: arrow.get(x))
    dff['arrival_date'] = dff['arrival_time'].apply(lambda x: x.date())
    dff['depature_time'] = dff['depature_time'].apply(lambda x: arrow.get(x))
    dff['depature_date'] = dff['depature_time'].apply(lambda x: x.date())
    
    # sort columns based on arrival time
    dff = dff.sort_values(by='arrival_time',ascending=True)

    # drop columns
    dff = dff[['arrival_delay', 'arrival_time', 'arrival_date', 'depature_delay', 'depature_time', 'depature_date', 'stop_id', 'stop_sequence', 'trip_id']]
    trips = trips[['route_id', 'service_id', 'trip_id','trip_headsign', 'direction_id']]
    stops = stops[stops.columns[:2]]
    
    # merge columns
    merged = pd.merge(left=stops, left_on='stop_id', right=dff, right_on='stop_id', how='right')
    merged = pd.merge(left=trips, left_on='trip_id', right=merged, right_on='trip_id', how='right')
    print('|     Dates    |\n----------------')
    for i in sorted(merged['arrival_date'].unique()):
        print('|  {}  |'.format(str(i)))
    return merged
```


```python
# lists the dates present in the dataframe
def listDates(df):
    for i in sorted(df['arrival_date'].unique()):
        print('|  {}  |'.format(str(i)))
```


```python
# gets the specified group (route_id) and can plot
def getGroup(df, group, plot=False):
    data = []
    grouped = df.groupby('route_id').get_group(group)
    print('Number of trips: {}'.format(len(grouped['trip_id'].unique())))
    if plot:
        for trips in grouped['trip_id'].unique():
            trip_ = grouped[grouped['trip_id'] == trips]
            trace = go.Scatter(
            x = trip_['arrival_time'].apply(lambda x: x.replace(tzinfo=None)),
            y = trip_['stop_sequence'],
            name = trips)
            data.append(trace)
        fig = go.Figure(data)
        iplot(fig)
    return grouped
```


```python
# plot arrival times across stop sequences
def plotArrival(df):
    data = []
    for trips in df['trip_id'].unique():
        trip_ = df[df['trip_id'] == trips]
        trace = go.Scatter(
        x = trip_['arrival_time'],
        y = trip_['stop_sequence'],
        name = trips)
        data.append(trace)
    fig = go.Figure(data)
    iplot(fig)
```


```python
# calculates delay and returns scheduled datetime
def calculateDelays(df, arrival=True):
    scheduled_times = []
    col = 'arrival' if arrival else 'depature'
    for idx, row in df.iterrows():
        delay = int(row[col+'_delay'] * -1)
        scheduled_times.append(row[col+'_time'].shift(seconds=delay))
    return scheduled_times
```


```python
# adds scheduled times to the dataframe
def getDelays(df):
    df['sched_arrival'] = calculateDelays(df)
    df['sched_depature'] = calculateDelays(df, arrival=False)
    return df
```


```python
# plots a trip and compares actual and scheduled arrival
def plotDelayedTrip(qGrid_filtered):
    data = []
    trip_ = qGrid_filtered.get_changed_df()
    selected = qGrid_filtered.get_changed_df()['trip_id'].unique()[0]
    trip_ = trip_[trip_['trip_id'] == selected]

    trace = go.Scatter(
        x = trip_['arrival_time'],
        y = trip_['stop_sequence'],
        name = 'Actual Time')
    data.append(trace)
    trace = go.Scatter(
        x = trip_['sched_arrival'],
        y = trip_['stop_sequence'],
        name = 'Scheduled Time')
    data.append(trace)
    
    layout = go.Layout(title = 'Trip ' + selected)
    fig = go.Figure(data, layout)
    iplot(fig)
```


```python
# def plotDelays():
#     df['arrival_time'].iloc[0].shift(seconds=-129)
```

# Acquire Data


```python
# set credentials to acquire data from Socr"ata
client = Socrata('www.data.act.gov.au',
                 '4jqogoRJ9NKj1gr8QAZ9CCKFI',
                 username=credentials['username'],
                 password=credentials['password'])
```


```python
# get data from endpoint
results = client.get("jxpp-4iiz", limit=25000)
```


```python
# Convert to pandas DataFrame
results_df = pd.DataFrame.from_records(results)
```


```python
# get data from trips
trips = pd.read_csv('../google_transit_lr/trips.csv')
```


```python
stops = pd.read_csv('../google_transit_lr/stops.csv')
```

# Convert, Sort, Drop, Merge Columns


```python
df = CSDM(results_df, trips, stops)
```

    |     Dates    |
    ----------------
    |  2019-06-19  |
    |  2019-06-20  |
    |  2019-06-21  |
    |  2019-06-22  |
    |  2019-06-23  |
    |  2019-06-24  |
    |  2019-06-25  |
    |  2019-06-26  |
    |  2019-06-27  |



```python
# TODO: FILTER A DATE
qgrid_filtered = qgrid.show_grid(df)
qgrid_filtered
```


    QgridWidget(grid_options={'fullWidthRows': True, 'syncColumnCellResize': True, 'forceFitColumns': True, 'defau…



```python
selected_date = qgrid_filtered.get_changed_df()
print('Selected date: ', str(selected_date['arrival_date'].unique()[0]))
print('Total Trips: ', len(selected_date['trip_id'].unique()))
```

    Selected date:  2019-06-26
    Total Trips:  240



```python
selected_date
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>route_id</th>
      <th>service_id</th>
      <th>trip_id</th>
      <th>trip_headsign</th>
      <th>direction_id</th>
      <th>stop_id</th>
      <th>stop_name</th>
      <th>arrival_delay</th>
      <th>arrival_time</th>
      <th>arrival_date</th>
      <th>depature_delay</th>
      <th>depature_time</th>
      <th>depature_date</th>
      <th>stop_sequence</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>1763</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>135</td>
      <td>Alinga St</td>
      <td>1.0</td>
      <td>8100</td>
      <td>Gungahlin Place Platform 1</td>
      <td>0</td>
      <td>2019-06-26T06:00:00+00:00</td>
      <td>2019-06-26</td>
      <td>0</td>
      <td>2019-06-26T06:00:00+00:00</td>
      <td>2019-06-26</td>
      <td>1</td>
    </tr>
    <tr>
      <th>1767</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>135</td>
      <td>Alinga St</td>
      <td>1.0</td>
      <td>8104</td>
      <td>Manning Clark Crescent Platform 1</td>
      <td>30</td>
      <td>2019-06-26T06:02:34+00:00</td>
      <td>2019-06-26</td>
      <td>30</td>
      <td>2019-06-26T06:02:54+00:00</td>
      <td>2019-06-26</td>
      <td>2</td>
    </tr>
    <tr>
      <th>1771</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>135</td>
      <td>Alinga St</td>
      <td>1.0</td>
      <td>8106</td>
      <td>Mapleton Avenue Platform 1</td>
      <td>55</td>
      <td>2019-06-26T06:04:59+00:00</td>
      <td>2019-06-26</td>
      <td>55</td>
      <td>2019-06-26T06:05:19+00:00</td>
      <td>2019-06-26</td>
      <td>3</td>
    </tr>
    <tr>
      <th>1775</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>135</td>
      <td>Alinga St</td>
      <td>1.0</td>
      <td>8108</td>
      <td>Nullarbor Avenue Platform 1</td>
      <td>47</td>
      <td>2019-06-26T06:06:27+00:00</td>
      <td>2019-06-26</td>
      <td>47</td>
      <td>2019-06-26T06:06:47+00:00</td>
      <td>2019-06-26</td>
      <td>4</td>
    </tr>
    <tr>
      <th>1779</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>135</td>
      <td>Alinga St</td>
      <td>1.0</td>
      <td>8110</td>
      <td>Well Station Drive Platform 1</td>
      <td>40</td>
      <td>2019-06-26T06:08:11+00:00</td>
      <td>2019-06-26</td>
      <td>40</td>
      <td>2019-06-26T06:08:31+00:00</td>
      <td>2019-06-26</td>
      <td>5</td>
    </tr>
    <tr>
      <th>1783</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>135</td>
      <td>Alinga St</td>
      <td>1.0</td>
      <td>8114</td>
      <td>EPIC and Racecourse Platform 1</td>
      <td>48</td>
      <td>2019-06-26T06:11:57+00:00</td>
      <td>2019-06-26</td>
      <td>48</td>
      <td>2019-06-26T06:12:17+00:00</td>
      <td>2019-06-26</td>
      <td>6</td>
    </tr>
    <tr>
      <th>1787</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>135</td>
      <td>Alinga St</td>
      <td>1.0</td>
      <td>8116</td>
      <td>Phillip Avenue Platform 1</td>
      <td>17</td>
      <td>2019-06-26T06:13:42+00:00</td>
      <td>2019-06-26</td>
      <td>17</td>
      <td>2019-06-26T06:14:02+00:00</td>
      <td>2019-06-26</td>
      <td>7</td>
    </tr>
    <tr>
      <th>1791</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>135</td>
      <td>Alinga St</td>
      <td>1.0</td>
      <td>8118</td>
      <td>Swinden Street Platform 1</td>
      <td>19</td>
      <td>2019-06-26T06:15:53+00:00</td>
      <td>2019-06-26</td>
      <td>19</td>
      <td>2019-06-26T06:16:13+00:00</td>
      <td>2019-06-26</td>
      <td>8</td>
    </tr>
    <tr>
      <th>1795</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>135</td>
      <td>Alinga St</td>
      <td>1.0</td>
      <td>8120</td>
      <td>Dickson Platform 1</td>
      <td>6</td>
      <td>2019-06-26T06:17:23+00:00</td>
      <td>2019-06-26</td>
      <td>6</td>
      <td>2019-06-26T06:17:43+00:00</td>
      <td>2019-06-26</td>
      <td>9</td>
    </tr>
    <tr>
      <th>1799</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>135</td>
      <td>Alinga St</td>
      <td>1.0</td>
      <td>8122</td>
      <td>Macarthur Avenue Platform 1</td>
      <td>17</td>
      <td>2019-06-26T06:19:34+00:00</td>
      <td>2019-06-26</td>
      <td>17</td>
      <td>2019-06-26T06:19:54+00:00</td>
      <td>2019-06-26</td>
      <td>10</td>
    </tr>
    <tr>
      <th>1803</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>135</td>
      <td>Alinga St</td>
      <td>1.0</td>
      <td>8124</td>
      <td>Ipima Street Platform 1</td>
      <td>25</td>
      <td>2019-06-26T06:21:00+00:00</td>
      <td>2019-06-26</td>
      <td>25</td>
      <td>2019-06-26T06:21:20+00:00</td>
      <td>2019-06-26</td>
      <td>11</td>
    </tr>
    <tr>
      <th>1807</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>135</td>
      <td>Alinga St</td>
      <td>1.0</td>
      <td>8126</td>
      <td>Elouera Street Platform 1</td>
      <td>26</td>
      <td>2019-06-26T06:22:39+00:00</td>
      <td>2019-06-26</td>
      <td>26</td>
      <td>2019-06-26T06:22:59+00:00</td>
      <td>2019-06-26</td>
      <td>12</td>
    </tr>
    <tr>
      <th>1813</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>135</td>
      <td>Alinga St</td>
      <td>1.0</td>
      <td>8129</td>
      <td>Alinga Street Platform 2</td>
      <td>33</td>
      <td>2019-06-26T06:24:33+00:00</td>
      <td>2019-06-26</td>
      <td>33</td>
      <td>2019-06-26T06:24:33+00:00</td>
      <td>2019-06-26</td>
      <td>13</td>
    </tr>
    <tr>
      <th>1819</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>7</td>
      <td>Gungahlin Pl</td>
      <td>0.0</td>
      <td>8100</td>
      <td>Gungahlin Place Platform 1</td>
      <td>120</td>
      <td>2019-06-26T06:56:00+00:00</td>
      <td>2019-06-26</td>
      <td>120</td>
      <td>2019-06-26T06:56:00+00:00</td>
      <td>2019-06-26</td>
      <td>13</td>
    </tr>
    <tr>
      <th>1823</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>7</td>
      <td>Gungahlin Pl</td>
      <td>0.0</td>
      <td>8105</td>
      <td>Manning Clark Crescent Platform 2</td>
      <td>107</td>
      <td>2019-06-26T06:53:49+00:00</td>
      <td>2019-06-26</td>
      <td>107</td>
      <td>2019-06-26T06:54:09+00:00</td>
      <td>2019-06-26</td>
      <td>12</td>
    </tr>
    <tr>
      <th>1827</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>7</td>
      <td>Gungahlin Pl</td>
      <td>0.0</td>
      <td>8107</td>
      <td>Mapleton Avenue Platform 2</td>
      <td>97</td>
      <td>2019-06-26T06:51:45+00:00</td>
      <td>2019-06-26</td>
      <td>97</td>
      <td>2019-06-26T06:52:05+00:00</td>
      <td>2019-06-26</td>
      <td>11</td>
    </tr>
    <tr>
      <th>1831</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>7</td>
      <td>Gungahlin Pl</td>
      <td>0.0</td>
      <td>8109</td>
      <td>Nullarbor Avenue Platform 2</td>
      <td>90</td>
      <td>2019-06-26T06:50:07+00:00</td>
      <td>2019-06-26</td>
      <td>90</td>
      <td>2019-06-26T06:50:27+00:00</td>
      <td>2019-06-26</td>
      <td>10</td>
    </tr>
    <tr>
      <th>1835</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>7</td>
      <td>Gungahlin Pl</td>
      <td>0.0</td>
      <td>8111</td>
      <td>Well Station Drive Platform 2</td>
      <td>37</td>
      <td>2019-06-26T06:47:10+00:00</td>
      <td>2019-06-26</td>
      <td>37</td>
      <td>2019-06-26T06:47:30+00:00</td>
      <td>2019-06-26</td>
      <td>9</td>
    </tr>
    <tr>
      <th>1839</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>7</td>
      <td>Gungahlin Pl</td>
      <td>0.0</td>
      <td>8115</td>
      <td>EPIC and Racecourse Platform 2</td>
      <td>78</td>
      <td>2019-06-26T06:44:18+00:00</td>
      <td>2019-06-26</td>
      <td>78</td>
      <td>2019-06-26T06:44:38+00:00</td>
      <td>2019-06-26</td>
      <td>8</td>
    </tr>
    <tr>
      <th>1843</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>7</td>
      <td>Gungahlin Pl</td>
      <td>0.0</td>
      <td>8117</td>
      <td>Phillip Avenue Platform 2</td>
      <td>82</td>
      <td>2019-06-26T06:42:07+00:00</td>
      <td>2019-06-26</td>
      <td>82</td>
      <td>2019-06-26T06:42:27+00:00</td>
      <td>2019-06-26</td>
      <td>7</td>
    </tr>
    <tr>
      <th>1847</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>7</td>
      <td>Gungahlin Pl</td>
      <td>0.0</td>
      <td>8119</td>
      <td>Swinden Street Platform 2</td>
      <td>74</td>
      <td>2019-06-26T06:39:55+00:00</td>
      <td>2019-06-26</td>
      <td>74</td>
      <td>2019-06-26T06:40:15+00:00</td>
      <td>2019-06-26</td>
      <td>6</td>
    </tr>
    <tr>
      <th>1851</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>7</td>
      <td>Gungahlin Pl</td>
      <td>0.0</td>
      <td>8121</td>
      <td>Dickson Platform 2</td>
      <td>89</td>
      <td>2019-06-26T06:38:13+00:00</td>
      <td>2019-06-26</td>
      <td>89</td>
      <td>2019-06-26T06:38:33+00:00</td>
      <td>2019-06-26</td>
      <td>5</td>
    </tr>
    <tr>
      <th>1855</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>7</td>
      <td>Gungahlin Pl</td>
      <td>0.0</td>
      <td>8123</td>
      <td>Macarthur Avenue Platform 2</td>
      <td>88</td>
      <td>2019-06-26T06:36:13+00:00</td>
      <td>2019-06-26</td>
      <td>88</td>
      <td>2019-06-26T06:36:33+00:00</td>
      <td>2019-06-26</td>
      <td>4</td>
    </tr>
    <tr>
      <th>1859</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>7</td>
      <td>Gungahlin Pl</td>
      <td>0.0</td>
      <td>8125</td>
      <td>Ipima Street Platform 2</td>
      <td>83</td>
      <td>2019-06-26T06:34:47+00:00</td>
      <td>2019-06-26</td>
      <td>83</td>
      <td>2019-06-26T06:35:07+00:00</td>
      <td>2019-06-26</td>
      <td>3</td>
    </tr>
    <tr>
      <th>1863</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>7</td>
      <td>Gungahlin Pl</td>
      <td>0.0</td>
      <td>8127</td>
      <td>Elouera Street Platform 2</td>
      <td>69</td>
      <td>2019-06-26T06:33:03+00:00</td>
      <td>2019-06-26</td>
      <td>69</td>
      <td>2019-06-26T06:33:23+00:00</td>
      <td>2019-06-26</td>
      <td>2</td>
    </tr>
    <tr>
      <th>1867</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>7</td>
      <td>Gungahlin Pl</td>
      <td>0.0</td>
      <td>8129</td>
      <td>Alinga Street Platform 2</td>
      <td>0</td>
      <td>2019-06-26T06:30:00+00:00</td>
      <td>2019-06-26</td>
      <td>0</td>
      <td>2019-06-26T06:30:00+00:00</td>
      <td>2019-06-26</td>
      <td>1</td>
    </tr>
    <tr>
      <th>1871</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>141</td>
      <td>Alinga St</td>
      <td>1.0</td>
      <td>8100</td>
      <td>Gungahlin Place Platform 1</td>
      <td>0</td>
      <td>2019-06-26T07:00:00+00:00</td>
      <td>2019-06-26</td>
      <td>0</td>
      <td>2019-06-26T07:00:00+00:00</td>
      <td>2019-06-26</td>
      <td>1</td>
    </tr>
    <tr>
      <th>1875</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>141</td>
      <td>Alinga St</td>
      <td>1.0</td>
      <td>8104</td>
      <td>Manning Clark Crescent Platform 1</td>
      <td>1</td>
      <td>2019-06-26T07:02:05+00:00</td>
      <td>2019-06-26</td>
      <td>1</td>
      <td>2019-06-26T07:02:25+00:00</td>
      <td>2019-06-26</td>
      <td>2</td>
    </tr>
    <tr>
      <th>1879</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>141</td>
      <td>Alinga St</td>
      <td>1.0</td>
      <td>8106</td>
      <td>Mapleton Avenue Platform 1</td>
      <td>13</td>
      <td>2019-06-26T07:04:17+00:00</td>
      <td>2019-06-26</td>
      <td>13</td>
      <td>2019-06-26T07:04:37+00:00</td>
      <td>2019-06-26</td>
      <td>3</td>
    </tr>
    <tr>
      <th>1883</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>141</td>
      <td>Alinga St</td>
      <td>1.0</td>
      <td>8108</td>
      <td>Nullarbor Avenue Platform 1</td>
      <td>17</td>
      <td>2019-06-26T07:05:57+00:00</td>
      <td>2019-06-26</td>
      <td>17</td>
      <td>2019-06-26T07:06:17+00:00</td>
      <td>2019-06-26</td>
      <td>4</td>
    </tr>
    <tr>
      <th>...</th>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
      <td>...</td>
    </tr>
    <tr>
      <th>15631</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>230</td>
      <td>Alinga St</td>
      <td>1.0</td>
      <td>8129</td>
      <td>Alinga Street Platform 2</td>
      <td>0</td>
      <td>2019-06-26T18:14:00+00:00</td>
      <td>2019-06-26</td>
      <td>0</td>
      <td>2019-06-26T18:14:00+00:00</td>
      <td>2019-06-26</td>
      <td>13</td>
    </tr>
    <tr>
      <th>15636</th>
      <td>X2</td>
      <td>WD</td>
      <td>109</td>
      <td>EPIC</td>
      <td>0.0</td>
      <td>8115</td>
      <td>EPIC and Racecourse Platform 2</td>
      <td>0</td>
      <td>2019-06-26T18:30:00+00:00</td>
      <td>2019-06-26</td>
      <td>0</td>
      <td>2019-06-26T18:30:00+00:00</td>
      <td>2019-06-26</td>
      <td>8</td>
    </tr>
    <tr>
      <th>15641</th>
      <td>X2</td>
      <td>WD</td>
      <td>109</td>
      <td>EPIC</td>
      <td>0.0</td>
      <td>8117</td>
      <td>Phillip Avenue Platform 2</td>
      <td>0</td>
      <td>2019-06-26T18:27:45+00:00</td>
      <td>2019-06-26</td>
      <td>0</td>
      <td>2019-06-26T18:28:05+00:00</td>
      <td>2019-06-26</td>
      <td>7</td>
    </tr>
    <tr>
      <th>15646</th>
      <td>X2</td>
      <td>WD</td>
      <td>109</td>
      <td>EPIC</td>
      <td>0.0</td>
      <td>8119</td>
      <td>Swinden Street Platform 2</td>
      <td>0</td>
      <td>2019-06-26T18:25:41+00:00</td>
      <td>2019-06-26</td>
      <td>0</td>
      <td>2019-06-26T18:26:01+00:00</td>
      <td>2019-06-26</td>
      <td>6</td>
    </tr>
    <tr>
      <th>15651</th>
      <td>X2</td>
      <td>WD</td>
      <td>109</td>
      <td>EPIC</td>
      <td>0.0</td>
      <td>8121</td>
      <td>Dickson Platform 2</td>
      <td>0</td>
      <td>2019-06-26T18:23:44+00:00</td>
      <td>2019-06-26</td>
      <td>0</td>
      <td>2019-06-26T18:24:04+00:00</td>
      <td>2019-06-26</td>
      <td>5</td>
    </tr>
    <tr>
      <th>15656</th>
      <td>X2</td>
      <td>WD</td>
      <td>109</td>
      <td>EPIC</td>
      <td>0.0</td>
      <td>8123</td>
      <td>Macarthur Avenue Platform 2</td>
      <td>0</td>
      <td>2019-06-26T18:21:45+00:00</td>
      <td>2019-06-26</td>
      <td>0</td>
      <td>2019-06-26T18:22:05+00:00</td>
      <td>2019-06-26</td>
      <td>4</td>
    </tr>
    <tr>
      <th>15661</th>
      <td>X2</td>
      <td>WD</td>
      <td>109</td>
      <td>EPIC</td>
      <td>0.0</td>
      <td>8125</td>
      <td>Ipima Street Platform 2</td>
      <td>0</td>
      <td>2019-06-26T18:20:24+00:00</td>
      <td>2019-06-26</td>
      <td>0</td>
      <td>2019-06-26T18:20:44+00:00</td>
      <td>2019-06-26</td>
      <td>3</td>
    </tr>
    <tr>
      <th>15666</th>
      <td>X2</td>
      <td>WD</td>
      <td>109</td>
      <td>EPIC</td>
      <td>0.0</td>
      <td>8127</td>
      <td>Elouera Street Platform 2</td>
      <td>0</td>
      <td>2019-06-26T18:18:54+00:00</td>
      <td>2019-06-26</td>
      <td>0</td>
      <td>2019-06-26T18:19:14+00:00</td>
      <td>2019-06-26</td>
      <td>2</td>
    </tr>
    <tr>
      <th>15671</th>
      <td>X2</td>
      <td>WD</td>
      <td>109</td>
      <td>EPIC</td>
      <td>0.0</td>
      <td>8129</td>
      <td>Alinga Street Platform 2</td>
      <td>0</td>
      <td>2019-06-26T18:17:00+00:00</td>
      <td>2019-06-26</td>
      <td>0</td>
      <td>2019-06-26T18:17:00+00:00</td>
      <td>2019-06-26</td>
      <td>1</td>
    </tr>
    <tr>
      <th>21440</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>R1</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>8100</td>
      <td>Gungahlin Place Platform 1</td>
      <td>48</td>
      <td>2019-06-26T16:09:54+00:00</td>
      <td>2019-06-26</td>
      <td>48</td>
      <td>2019-06-26T16:09:54+00:00</td>
      <td>2019-06-26</td>
      <td>13</td>
    </tr>
    <tr>
      <th>21445</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>R1</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>8105</td>
      <td>Manning Clark Crescent Platform 2</td>
      <td>48</td>
      <td>2019-06-26T16:07:56+00:00</td>
      <td>2019-06-26</td>
      <td>48</td>
      <td>2019-06-26T16:08:16+00:00</td>
      <td>2019-06-26</td>
      <td>12</td>
    </tr>
    <tr>
      <th>21450</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>R1</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>8107</td>
      <td>Mapleton Avenue Platform 2</td>
      <td>48</td>
      <td>2019-06-26T16:06:02+00:00</td>
      <td>2019-06-26</td>
      <td>48</td>
      <td>2019-06-26T16:06:22+00:00</td>
      <td>2019-06-26</td>
      <td>11</td>
    </tr>
    <tr>
      <th>21455</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>R1</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>8109</td>
      <td>Nullarbor Avenue Platform 2</td>
      <td>40</td>
      <td>2019-06-26T16:04:23+00:00</td>
      <td>2019-06-26</td>
      <td>40</td>
      <td>2019-06-26T16:04:43+00:00</td>
      <td>2019-06-26</td>
      <td>10</td>
    </tr>
    <tr>
      <th>21460</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>R1</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>8111</td>
      <td>Well Station Drive Platform 2</td>
      <td>66</td>
      <td>2019-06-26T16:02:45+00:00</td>
      <td>2019-06-26</td>
      <td>66</td>
      <td>2019-06-26T16:03:05+00:00</td>
      <td>2019-06-26</td>
      <td>9</td>
    </tr>
    <tr>
      <th>21465</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>R1</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>8115</td>
      <td>EPIC and Racecourse Platform 2</td>
      <td>-11</td>
      <td>2019-06-26T15:57:55+00:00</td>
      <td>2019-06-26</td>
      <td>-11</td>
      <td>2019-06-26T15:58:15+00:00</td>
      <td>2019-06-26</td>
      <td>8</td>
    </tr>
    <tr>
      <th>21470</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>R1</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>8117</td>
      <td>Phillip Avenue Platform 2</td>
      <td>-20</td>
      <td>2019-06-26T15:55:31+00:00</td>
      <td>2019-06-26</td>
      <td>-20</td>
      <td>2019-06-26T15:55:51+00:00</td>
      <td>2019-06-26</td>
      <td>7</td>
    </tr>
    <tr>
      <th>21475</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>R1</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>8119</td>
      <td>Swinden Street Platform 2</td>
      <td>-21</td>
      <td>2019-06-26T15:53:26+00:00</td>
      <td>2019-06-26</td>
      <td>-21</td>
      <td>2019-06-26T15:53:46+00:00</td>
      <td>2019-06-26</td>
      <td>6</td>
    </tr>
    <tr>
      <th>21480</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>R1</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>8121</td>
      <td>Dickson Platform 2</td>
      <td>5</td>
      <td>2019-06-26T15:51:55+00:00</td>
      <td>2019-06-26</td>
      <td>5</td>
      <td>2019-06-26T15:52:15+00:00</td>
      <td>2019-06-26</td>
      <td>5</td>
    </tr>
    <tr>
      <th>21485</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>R1</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>8123</td>
      <td>Macarthur Avenue Platform 2</td>
      <td>-13</td>
      <td>2019-06-26T15:49:38+00:00</td>
      <td>2019-06-26</td>
      <td>-13</td>
      <td>2019-06-26T15:49:58+00:00</td>
      <td>2019-06-26</td>
      <td>4</td>
    </tr>
    <tr>
      <th>21490</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>R1</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>8125</td>
      <td>Ipima Street Platform 2</td>
      <td>-19</td>
      <td>2019-06-26T15:48:11+00:00</td>
      <td>2019-06-26</td>
      <td>-19</td>
      <td>2019-06-26T15:48:31+00:00</td>
      <td>2019-06-26</td>
      <td>3</td>
    </tr>
    <tr>
      <th>21495</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>R1</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>8127</td>
      <td>Elouera Street Platform 2</td>
      <td>-23</td>
      <td>2019-06-26T15:46:37+00:00</td>
      <td>2019-06-26</td>
      <td>-23</td>
      <td>2019-06-26T15:46:57+00:00</td>
      <td>2019-06-26</td>
      <td>2</td>
    </tr>
    <tr>
      <th>21499</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>R1</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>8128</td>
      <td>Alinga Street Platform 1</td>
      <td>0</td>
      <td>2019-06-26T15:45:00+00:00</td>
      <td>2019-06-26</td>
      <td>0</td>
      <td>2019-06-26T15:45:00+00:00</td>
      <td>2019-06-26</td>
      <td>1</td>
    </tr>
    <tr>
      <th>21611</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>R2</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>8114</td>
      <td>EPIC and Racecourse Platform 1</td>
      <td>0</td>
      <td>2019-06-26T15:25:44+00:00</td>
      <td>2019-06-26</td>
      <td>0</td>
      <td>2019-06-26T15:25:44+00:00</td>
      <td>2019-06-26</td>
      <td>1</td>
    </tr>
    <tr>
      <th>21613</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>R2</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>8116</td>
      <td>Phillip Avenue Platform 1</td>
      <td>54</td>
      <td>2019-06-26T15:28:54+00:00</td>
      <td>2019-06-26</td>
      <td>54</td>
      <td>2019-06-26T15:29:14+00:00</td>
      <td>2019-06-26</td>
      <td>2</td>
    </tr>
    <tr>
      <th>21615</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>R2</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>8118</td>
      <td>Swinden Street Platform 1</td>
      <td>4</td>
      <td>2019-06-26T15:30:13+00:00</td>
      <td>2019-06-26</td>
      <td>4</td>
      <td>2019-06-26T15:30:33+00:00</td>
      <td>2019-06-26</td>
      <td>3</td>
    </tr>
    <tr>
      <th>21617</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>R2</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>8120</td>
      <td>Dickson Platform 1</td>
      <td>-13</td>
      <td>2019-06-26T15:31:39+00:00</td>
      <td>2019-06-26</td>
      <td>-13</td>
      <td>2019-06-26T15:31:59+00:00</td>
      <td>2019-06-26</td>
      <td>4</td>
    </tr>
    <tr>
      <th>21619</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>R2</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>8122</td>
      <td>Macarthur Avenue Platform 1</td>
      <td>13</td>
      <td>2019-06-26T15:34:05+00:00</td>
      <td>2019-06-26</td>
      <td>13</td>
      <td>2019-06-26T15:34:25+00:00</td>
      <td>2019-06-26</td>
      <td>5</td>
    </tr>
    <tr>
      <th>21621</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>R2</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>8124</td>
      <td>Ipima Street Platform 1</td>
      <td>14</td>
      <td>2019-06-26T15:35:24+00:00</td>
      <td>2019-06-26</td>
      <td>14</td>
      <td>2019-06-26T15:35:44+00:00</td>
      <td>2019-06-26</td>
      <td>6</td>
    </tr>
    <tr>
      <th>21623</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>R2</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>8126</td>
      <td>Elouera Street Platform 1</td>
      <td>15</td>
      <td>2019-06-26T15:37:03+00:00</td>
      <td>2019-06-26</td>
      <td>15</td>
      <td>2019-06-26T15:37:23+00:00</td>
      <td>2019-06-26</td>
      <td>7</td>
    </tr>
    <tr>
      <th>21626</th>
      <td>NaN</td>
      <td>NaN</td>
      <td>R2</td>
      <td>NaN</td>
      <td>NaN</td>
      <td>8128</td>
      <td>Alinga Street Platform 1</td>
      <td>1</td>
      <td>2019-06-26T15:38:49+00:00</td>
      <td>2019-06-26</td>
      <td>1</td>
      <td>2019-06-26T15:38:49+00:00</td>
      <td>2019-06-26</td>
      <td>8</td>
    </tr>
  </tbody>
</table>
<p>2928 rows × 14 columns</p>
</div>



# Group Routes


```python
full_trip = getGroup(selected_date, 'ACTO001', plot=False)
```

    Number of trips: 212



```python
x1 = getGroup(selected_date, 'X1', plot=False)
```

    Number of trips: 19



```python
x2 = getGroup(selected_date, 'X2', plot=False)
```

    Number of trips: 7


# Understanding Delays


```python
full_trip = getDelays(full_trip)
```

    /anaconda3/envs/data-science/lib/python3.6/site-packages/ipykernel_launcher.py:3: SettingWithCopyWarning:
    
    
    A value is trying to be set on a copy of a slice from a DataFrame.
    Try using .loc[row_indexer,col_indexer] = value instead
    
    See the caveats in the documentation: http://pandas.pydata.org/pandas-docs/stable/indexing.html#indexing-view-versus-copy
    
    /anaconda3/envs/data-science/lib/python3.6/site-packages/ipykernel_launcher.py:4: SettingWithCopyWarning:
    
    
    A value is trying to be set on a copy of a slice from a DataFrame.
    Try using .loc[row_indexer,col_indexer] = value instead
    
    See the caveats in the documentation: http://pandas.pydata.org/pandas-docs/stable/indexing.html#indexing-view-versus-copy
    



```python
qgrid_filtered = qgrid.show_grid(full_trip[['trip_id', 'sched_arrival', 'arrival_time', 'arrival_delay', 'sched_depature','depature_time', 'arrival_delay', 'stop_sequence', 'trip_headsign', 'stop_name']])
qgrid_filtered
```


    QgridWidget(grid_options={'fullWidthRows': True, 'syncColumnCellResize': True, 'forceFitColumns': True, 'defau…



```python
# TODO: FILTER FIRST BEFORE USING THIS FUNCTION
plotDelayedTrip(qgrid_filtered)
```


<div id="e1700b9e-c4d5-4dcb-9401-3af91f77168d" style="height: 525px; width: 100%;" class="plotly-graph-div"></div><script type="text/javascript">require(["plotly"], function(Plotly) { window.PLOTLYENV=window.PLOTLYENV || {};window.PLOTLYENV.BASE_URL="https://plot.ly";Plotly.newPlot("e1700b9e-c4d5-4dcb-9401-3af91f77168d", [{"name": "Actual Time", "x": ["2019-06-26 06:00:00", "2019-06-26 06:02:34", "2019-06-26 06:04:59", "2019-06-26 06:06:27", "2019-06-26 06:08:11", "2019-06-26 06:11:57", "2019-06-26 06:13:42", "2019-06-26 06:15:53", "2019-06-26 06:17:23", "2019-06-26 06:19:34", "2019-06-26 06:21:00", "2019-06-26 06:22:39", "2019-06-26 06:24:33"], "y": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13], "type": "scatter", "uid": "9fee4e76-4dea-4915-8db5-f838e86cbf43"}, {"name": "Scheduled Time", "x": ["2019-06-26 06:00:00", "2019-06-26 06:02:04", "2019-06-26 06:04:04", "2019-06-26 06:05:40", "2019-06-26 06:07:31", "2019-06-26 06:11:09", "2019-06-26 06:13:25", "2019-06-26 06:15:34", "2019-06-26 06:17:17", "2019-06-26 06:19:17", "2019-06-26 06:20:35", "2019-06-26 06:22:13", "2019-06-26 06:24:00"], "y": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13], "type": "scatter", "uid": "e5b38b06-091d-4e58-bedd-c00f2eb2045d"}], {"title": {"text": "Trip 135"}}, {"showLink": false, "linkText": "Export to plot.ly", "plotlyServerURL": "https://plot.ly"})});</script><script type="text/javascript">window.addEventListener("resize", function(){window._Plotly.Plots.resize(document.getElementById("e1700b9e-c4d5-4dcb-9401-3af91f77168d"));});</script>


# Understanding Missing Trips


```python
service_id = selected_date['service_id'].unique()[0]
print('Service ID: {}'.format(service_id))
```

    Service ID: WD



```python
grouped_service = trips.groupby('service_id').get_group(service_id)
grouped_service.head()
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>route_id</th>
      <th>service_id</th>
      <th>trip_id</th>
      <th>trip_headsign</th>
      <th>direction_id</th>
      <th>block_id</th>
      <th>shape_id</th>
      <th>wheelchair_accessible</th>
      <th>bikes_allowed</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>137</th>
      <td>NIS</td>
      <td>WD</td>
      <td>2</td>
      <td>Gungahlin Pl</td>
      <td>0</td>
      <td>4</td>
      <td>1007</td>
      <td>1</td>
      <td>1</td>
    </tr>
    <tr>
      <th>138</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>135</td>
      <td>Alinga St</td>
      <td>1</td>
      <td>4</td>
      <td>1003</td>
      <td>1</td>
      <td>1</td>
    </tr>
    <tr>
      <th>139</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>7</td>
      <td>Gungahlin Pl</td>
      <td>0</td>
      <td>4</td>
      <td>1004</td>
      <td>1</td>
      <td>1</td>
    </tr>
    <tr>
      <th>140</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>141</td>
      <td>Alinga St</td>
      <td>1</td>
      <td>4</td>
      <td>1003</td>
      <td>1</td>
      <td>1</td>
    </tr>
    <tr>
      <th>141</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>22</td>
      <td>Gungahlin Pl</td>
      <td>0</td>
      <td>4</td>
      <td>1004</td>
      <td>1</td>
      <td>1</td>
    </tr>
  </tbody>
</table>
</div>




```python
grouped_route = grouped_service.groupby('route_id').get_group('ACTO001')
grouped_route.head()
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>route_id</th>
      <th>service_id</th>
      <th>trip_id</th>
      <th>trip_headsign</th>
      <th>direction_id</th>
      <th>block_id</th>
      <th>shape_id</th>
      <th>wheelchair_accessible</th>
      <th>bikes_allowed</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>138</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>135</td>
      <td>Alinga St</td>
      <td>1</td>
      <td>4</td>
      <td>1003</td>
      <td>1</td>
      <td>1</td>
    </tr>
    <tr>
      <th>139</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>7</td>
      <td>Gungahlin Pl</td>
      <td>0</td>
      <td>4</td>
      <td>1004</td>
      <td>1</td>
      <td>1</td>
    </tr>
    <tr>
      <th>140</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>141</td>
      <td>Alinga St</td>
      <td>1</td>
      <td>4</td>
      <td>1003</td>
      <td>1</td>
      <td>1</td>
    </tr>
    <tr>
      <th>141</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>22</td>
      <td>Gungahlin Pl</td>
      <td>0</td>
      <td>4</td>
      <td>1004</td>
      <td>1</td>
      <td>1</td>
    </tr>
    <tr>
      <th>142</th>
      <td>ACTO001</td>
      <td>WD</td>
      <td>151</td>
      <td>Alinga St</td>
      <td>1</td>
      <td>4</td>
      <td>1003</td>
      <td>1</td>
      <td>1</td>
    </tr>
  </tbody>
</table>
</div>




```python
sched_trips = set(grouped_route['trip_id'])
print('Number of Scheduled Trips: ', len(sched_trips))
```

    Number of Scheduled Trips:  212



```python
print(sorted([int(i) for i in list(sched_trips)]))
```

    [5, 6, 7, 12, 15, 18, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 41, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 83, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 135, 136, 137, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 165, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 207, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 229, 230, 233, 236, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259]



```python
actual_trips = set(full_trip['trip_id'])
print('Number of Actual Trips: ', len(actual_trips))
```

    Number of Actual Trips:  212



```python
print(sorted([int(i) for i in list(actual_trips)]))
```

    [5, 6, 7, 12, 15, 18, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 41, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 83, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131, 135, 136, 137, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 165, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197, 198, 199, 200, 201, 202, 203, 204, 207, 210, 211, 212, 213, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 229, 230, 233, 236, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254, 255, 256, 257, 258, 259]



```python
# trips that happened which weren't supposed to 
actual_trips - sched_trips
```




    set()


