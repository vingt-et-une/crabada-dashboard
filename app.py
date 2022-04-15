import requests
import pandas as pd
import json
import plotly.express as px

crab_df = pd.concat([pd.read_json('1_10000.json'), pd.read_json('10000_21640.json').iloc[1: , :]]).reset_index(drop=True)
sales_df = pd.read_csv('2022-01-24-crabada-sales.csv')
sales_merged_df = sales_df.merge(crab_df, left_on='crab_id', right_on='id')
stats = ['hp','speed','damage','critical','armor']
normalized_stats_w = pd.concat([crab_df.id, (crab_df[stats]-crab_df[stats].min())/(crab_df[stats].max()-crab_df[stats].min())], axis=1)
# normalize stats and combine to get most efficient crabs
normalized_stats_l = pd.melt(normalized_stats_w, 'id',['hp','speed','damage','critical','armor'])
# px.bar(normalized_stats, 'id', 'value', color = 'variable')
normalized_stats_w['total'] = normalized_stats_w[['hp','speed','damage','critical','armor']].sum(axis=1)

# # Dashboard
# - We aim to understand what are the most popular types of crabs, stats, and other useful information we may come across. 
#   - Most popular crabs, parts, types
#   - Most popular stat distribution
#   - Pricing

class_list = ['BULK','PRIME','GEM','CRABOID','RUINED','SUNKEN','SURGE','ORGANIC']
class_bool = {crabada_class: sales_merged_df.class_name == crabada_class for crabada_class in class_list}
class_bool['ALL'] = sales_merged_df.class_name != ''

def create_price_hist(class_name):
    return px.histogram(sales_merged_df[class_bool[class_name]].total_price, title='Sales Breakdown').update_layout(showlegend=False)
def create_sales_scatt(class_name):
    return px.scatter(sales_merged_df[class_bool[class_name]], y='total_price', x='sale_timestamp', title='Price Over Time').update_layout(showlegend=False) 
def create_quant_hist(class_name):
    return px.histogram(sales_merged_df[class_bool[class_name]].sale_timestamp, title='Sales Count Over Time').update_layout(showlegend=False) 
sales_merged_df['Date'] = pd.to_datetime(sales_merged_df['sale_timestamp']) - pd.to_timedelta(7, unit='d')
def create_tot_sales_line(class_name): 
  return px.line(sales_merged_df[class_bool[class_name]].groupby(pd.Grouper(key='Date', freq='W-MON'))['total_price'].sum(), title='Total Weekly Sales').update_layout(showlegend=False) 
def create_parts_tbl(part):
  return pd.DataFrame(sales_merged_df[f'{part}_name'].value_counts().reset_index()).set_axis([f'{part} name',f'{part} count'], axis=1)
parts = ['shell','horn','mouth','eyes','pincers']
def create_part_pareto(i):
  part_pareto = create_parts_tbl(i)
  part_pareto['percent'] = ((part_pareto[f'{i} count']/part_pareto[f'{i} count'].sum())*100).cumsum()
  par = make_subplots(specs=[[{"secondary_y": True}]])
  par.add_trace(go.Scatter(y=part_pareto.percent, x=part_pareto[f'{i} name']),secondary_y=True)
  par.add_trace(go.Bar(y=part_pareto[f'{i} count'], x=part_pareto[f'{i} name']))
  par.update_layout(margin={'t': 20})
  return par
class_bar = px.bar(pd.DataFrame(sales_merged_df.class_name.value_counts()).rename(columns={'class_name':'count'}),title='Sold Class Breakdown').update_layout(showlegend=False) 
top_id_tbl = sales_merged_df.id.value_counts()

import plotly.graph_objects as go
from plotly.subplots import make_subplots

def helper_viz(fig,stats):
    fig.data[0].visible = True
    fig.data[1].visible = True
    steps = []
    for i in range(len(stats)):
        step = dict(
            method="update",
            args=[{"visible": [False] * len(fig.data)},
                {"title": f"Created vs Sold: {stats[i]}"}], 
        )
        step["args"][0]["visible"][i*2] = True
        step["args"][0]["visible"][i*2+1] = True
        steps.append(step)

    fig.update_layout(sliders=[dict(active=0, steps=steps, currentvalue={'visible':False})])
    return fig

fig = go.Figure()
for i in stats:
  fig.add_trace(go.Histogram(x=crab_df[i].dropna(), name="All"))
  fig.add_trace(go.Histogram(x=sales_merged_df[i].dropna(), name='Sold'))
  fig.update_layout(barmode='overlay')
  fig.update_traces(opacity=0.75)

stats_hist = helper_viz(fig, stats)
def crab_stat(id):
  fig = px.line_polar(normalized_stats_w[normalized_stats_w.id == id][stats].melt(),
                      theta='variable',
                      r='value',
                      line_close=True,
                      title=f'Crabada stats: Crabada {id}')
  fig.update_traces(fill='toself')
  return fig

from jupyter_dash import JupyterDash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output, State
from dash import dash_table

app = JupyterDash(__name__)
server = app.server

Intro = """"
# Crabada Market Guide v.1.0
A basic guide to the crabada economy 

* Data extracted: Jan 24, 2022
"""

app.layout = html.Div([
    html.Div(
          dcc.Markdown(Intro),
    ),
    html.H2(id="Sales and Prices"),
    html.Div(
          dcc.Dropdown(id='class_dropdown',
                       options=[{'label': i, 'value': i} for i in class_list]+[{'label': 'ALL', 'value': 'ALL'}],
                       value='ALL')
    ),
    html.Div(
          dcc.Graph(id='price_hist'),
          style={'width': '49%', 'display': 'inline-block'}
    ),
    html.Div(
          dcc.Graph(id='sales_scatt'),
          style={'width': '49%', 'display': 'inline-block'}
    ),
    html.Div(
          dcc.Graph(id='quant_hist'),
          style={'width': '49%', 'display': 'inline-block'}
    ),
    html.Div(
          dcc.Graph(id='tot_sales_line'),
          style={'width': '49%', 'display': 'inline-block'}
    ),
    html.H2("Popular Classes and Parts"),
    html.Div(
          dcc.Graph(figure=class_bar),
          style={'width': '49%', 'display': 'inline-block', 'verticalAlign': 'top'}
    ),
    html.Div([
          dcc.Dropdown(id='part_dropdown', options=[
                                          {'label':f'Parts Breakdown: {i}', 'value':i} for i in parts
                                      ],
                                      value='shell',
                                  ),
          dcc.Graph(id='part_pareto')
    ],
    style={'width': '49%', 'display': 'inline-block', 'verticalAlign': 'top'}),
    html.H2("Most Sought Stats and Crabada Stat Checker"),
    html.Div(
          dcc.Graph(figure=stats_hist),
          style={'width': '49%', 'display': 'inline-block','verticalAlign': 'top'},
    ),
    html.Div([
              dcc.Input(id='crab_id', value='1', type='number'),
              dcc.Graph(id='stat_radar')
    ],
    style={'width': '49%', 'display': 'inline-block','verticalAlign': 'top'},
    )
])
    
@app.callback(
    Output("Sales and Prices","children"),
    Output("price_hist", "figure"),
    Output("sales_scatt","figure"),
    Output("quant_hist","figure"),
    Output("tot_sales_line","figure"),
    Input('class_dropdown', 'value')
    )

def update_tables(value):
    text = f"Sales and Prices: {value}"
    return text, create_price_hist(value), create_sales_scatt(value), create_quant_hist(value),create_tot_sales_line(value)

@app.callback(
    Output("part_pareto", "figure"),
    Input('part_dropdown', 'value')
    )
def update_graph(value):
    return create_part_pareto(value)

@app.callback(
    Output("stat_radar", "figure"),
    Input("crab_id","value")
)
def update_radar(value):
  return crab_stat(value)


if __name__ == '__main__':
    app.run_server(debug=True)
