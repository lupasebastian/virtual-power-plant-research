import pandas as pd

from pvlib_predictions import pvlib_input_df
from utils import fetch_daily_household_demand_by_hour, BatteryStorage


def run_simulation_no_batteries(pv_generation_data: pd.DataFrame) -> None:
    overall_overproduction = 0
    overall_deficit = 0
    hours_met = 0
    hours_not_met = 0
    usage_df = fetch_daily_household_demand_by_hour()
    for row in pv_generation_data.itertuples():
        hourly_demand = usage_df.at[row.Index.hour, 'hourly_demand_in_kW']
        hourly_output = row.predicted_ac_kW
        hourly_overproduction, hourly_deficit = run_one_hour(hour=row.Index,
                                                             hourly_demand=hourly_demand, hourly_output=hourly_output)
        if not hourly_overproduction and not hourly_deficit:
            print('demand met perfectly, never gonna happen')
        elif hourly_overproduction:
            overall_overproduction += hourly_overproduction
            hours_met += 1
        elif hourly_deficit:
            overall_deficit += hourly_deficit
            hours_not_met += 1
    print(f"demand met in {hours_met} hours, not met in: {hours_not_met} hours, "
          f"overall deficit: {overall_deficit:.2f}, overall overproduction: {overall_overproduction:.2f}")

def run_simulation_one_battery_storage(pv_generation_data: pd.DataFrame):
    battery = BatteryStorage()
    battery.create_soc_history_frame(start=pv_generation_data.index[0],
                                     end=pv_generation_data.index[len(pv_generation_data) - 1],
                                     freq='h')
    usage_df = fetch_daily_household_demand_by_hour()
    for row in pv_generation_data.itertuples():
        hourly_demand = usage_df.at[row.Index.hour, 'hourly_demand_in_kW']
        hourly_output = row.predicted_ac_kW
        hourly_overproduction, hourly_deficit = run_one_hour(hour=row.Index, hourly_demand=hourly_demand, hourly_output=hourly_output)
        overflow = 0
        if not hourly_overproduction and not hourly_deficit:
            print('demand met perfectly, never gonna happen')
        elif hourly_overproduction:
            overflow = battery.charge(generation=hourly_overproduction)
            if overflow:
                print(f'overflow at {row.Index}: {overflow:.2f} kW')
        elif hourly_deficit:
            kW_from_battery = battery.discharge(load=hourly_deficit)
            if round(hourly_demand, ndigits=2) > round(hourly_output + kW_from_battery, ndigits=2):
                print(f'demand for {row.Index} not met: demand: {hourly_demand:.2f}, output + battery: {hourly_output + kW_from_battery:.2f}')
        battery.insert_step_into_history(row.Index, battery.state_of_charge, overflow)
    print(battery.soc_history)


def run_one_hour(hour, hourly_demand, hourly_output):
    overproduction = 0
    deficit = 0
    print(
        f'output for: {hour}, output: {hourly_output:.2f} kW, demand: {hourly_demand:.2f} kW')
    if hourly_demand < hourly_output:
        overproduction = hourly_output - hourly_demand
    elif hourly_demand > hourly_output:
        deficit = hourly_demand - hourly_output
    return overproduction, deficit

if __name__ == '__main__':
    run_simulation_no_batteries(pv_generation_data=pvlib_input_df)
    run_simulation_one_battery_storage(pv_generation_data=pvlib_input_df)
