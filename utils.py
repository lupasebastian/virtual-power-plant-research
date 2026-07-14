from openmeteo_sdk import VariableWithValues


def extract_weather_hourly_variables_by_name(hourly) -> dict:
    return {hourly.Variables(i).Variable(): hourly.Variables(i) for i in range(hourly.VariablesLength())}