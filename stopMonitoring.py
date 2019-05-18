# Import Libraries
from params import TC
import pandas as pd
import lxml.etree as etree
import requests

# Get Credentials
api = TC()

# API Parameters
api_token = api.token
api_url_base = api.url_base
api_endpoints = api.endpoints
api_service_name = api.service_name
