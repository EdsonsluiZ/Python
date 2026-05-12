# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

import plotly.express as px

country = input("Enter the Country name: ")
data = {
    'Country': [country],
    'Values': [100]
}

fig = px.choropleth (
    data,
    locations='Country',
    locationmode='country names',
    color='Values',
    color_continuous_scale='Inferno',
    title='Country Map Highlighting (country)'
)
fig.show()

#source code --> cloding.com