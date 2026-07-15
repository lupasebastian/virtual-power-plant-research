import calendar
import datetime

import openmeteo_requests
import pandas as pd
import pvlib
from openmeteo_sdk.Variable import Variable

from utils import extract_weather_hourly_variables_by_name
import config

openmeteo = openmeteo_requests.Client()

# TODO maybe add another forecast model and average results?
params = {
        "latitude": config.LATITUDE,
        "longitude": config.LONGITUDE,
        "hourly": ["shortwave_radiation", "direct_normal_irradiance", "diffuse_radiation", "temperature_2m",
                   "wind_speed_10m"],
        "timezone": config.TIMEZONE,
        "wind_speed_unit": "ms",
    }

# get forecast for tomorrow for local timezone (timestamps will be in utc, reflecting 2h shift)
if config.PERIOD[0] == 'tomorrow':
    tomorrow = datetime.datetime.now().date() + datetime.timedelta(days=1)
    params['start_date'] = tomorrow
    params['end_date'] = tomorrow
elif config.PERIOD[0] == 'month':
    month = config.PERIOD[1]
    start_of_month = datetime.datetime.now().date().replace(day=1, month=month)
    params['start_date'] = start_of_month
    _, last_day = calendar.monthrange(start_of_month.year, start_of_month.month)
    end_of_month = start_of_month.replace(day=last_day, month=month)
    params['end_date'] = end_of_month

url = config.WEATHER_API_URL
location = pvlib.location.Location(latitude=config.LATITUDE, longitude=config.LONGITUDE,
									   tz=config.TIMEZONE, altitude=166)

responses = openmeteo.weather_api(url, params=params)

response = responses[0]

print(f"Coordinates: {response.Latitude()}°N {response.Longitude()}°E")
print(f"Elevation: {response.Elevation()} m asl")
print(f"Timezone difference to GMT+0: {response.UtcOffsetSeconds()}s")

hourly = response.Hourly()

# data is returned from 00:00 utc, timestamps are read in utc, need to be aligned
utc_timestamps = pd.date_range(
    start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
    end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
    freq=pd.Timedelta(seconds=hourly.Interval()),
    inclusive="left",
	)

local_timestamps = pd.DatetimeIndex(utc_timestamps).tz_convert("Europe/Warsaw").tz_localize(None)

pvlib_input_df = pd.DataFrame(index=pd.Index(data=local_timestamps, name="datetime"))

extracted_variables = extract_weather_hourly_variables_by_name(hourly)

pvlib_input_df["ghi"] = extracted_variables[Variable.shortwave_radiation].ValuesAsNumpy()
pvlib_input_df["dni"] = extracted_variables[Variable.direct_normal_irradiance].ValuesAsNumpy()
pvlib_input_df["dhi"] = extracted_variables[Variable.diffuse_radiation].ValuesAsNumpy()
pvlib_input_df["temp_air"] = extracted_variables[Variable.temperature].ValuesAsNumpy()
pvlib_input_df["wind_speed"] = extracted_variables[Variable.wind_speed].ValuesAsNumpy()

# calculate all values in Watts
panel_power_w = config.PANEL_POWER_WATTS
number_of_panels = config.NUMBER_OF_PANELS
total_dc_power = panel_power_w * number_of_panels
print(f'total_dc_power: {total_dc_power}')

system = pvlib.pvsystem.PVSystem(
    surface_tilt=config.SURFACE_TILT,
    surface_azimuth=config.SURFACE_AZIMUTH,
    module_parameters={
        'pdc0': total_dc_power,
        'gamma_pdc': config.PANEL_TEMPERATURE_LOSS
    },
    inverter_parameters={
        'pdc0': total_dc_power,
        'eta_inv_nom': config.INVERTER_EFFICIENCY
    },
    temperature_model_parameters=pvlib.temperature.TEMPERATURE_MODEL_PARAMETERS['sapm']['open_rack_glass_glass'],
	losses_parameters={'soiling': 2, 'shading': 0, 'wiring': 2, 'connections': 0.5, 'mismatch': 2, 'availability': 1},
)

mc = pvlib.modelchain.ModelChain(
    system,
    location = location,
    transposition_model='perez',
    aoi_model='no_loss',
	losses_model='pvwatts'
)

mc.run_model(pvlib_input_df)

# convert predicted output to kW for readability
pvlib_input_df['predicted_dc_kW'] = pd.Series(mc.results.dc.fillna(0).clip(lower=0) / 1000, dtype='float64')
pvlib_input_df['predicted_ac_kW'] = pd.Series(mc.results.ac.fillna(0).clip(lower=0) / 1000, dtype='float64')

with pd.option_context('display.max_rows', None, 'display.max_columns', None):
    print(pvlib_input_df)

total_kwh = pvlib_input_df['predicted_ac_kW'].sum()
print(f"Total Expected Yield For Chosen Period ({config.PERIOD}): {total_kwh:.2f} kWh")