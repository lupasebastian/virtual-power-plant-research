import pandas as pd

import config


def extract_weather_hourly_variables_by_name(hourly) -> dict:
    return {hourly.Variables(i).Variable(): hourly.Variables(i) for i in range(hourly.VariablesLength())}


def fetch_daily_household_demand_by_hour() -> pd.DataFrame:
    # example hourly demand values for the Polish household profile in kW - usage varies hourly

    usage_df = pd.DataFrame(
        data=[
        0.154, 0.132, 0.121, 0.116, 0.126, 0.165,
        0.264, 0.319, 0.286, 0.231, 0.209, 0.198,
        0.220, 0.231, 0.242, 0.264, 0.308, 0.374,
        0.418, 0.451, 0.440, 0.374, 0.253, 0.209
    ],
        index=range(24),
        columns=['hourly_demand_in_kW'],
        dtype = 'float64'
    )
    return usage_df


class BatteryStorage():
    def __init__(self):
        self.capacity: float = config.BATTERY_STORAGE_CAPACITY_KILOWATTS
        self.state_of_charge: float = self.capacity
        self.soc_history = None

    def create_soc_history_frame(self, start, end, freq):
        self.soc_history = pd.DataFrame(
            index=pd.date_range(
                start=start, end=end, freq=freq),
            columns=['soc_at_timestamp'],
            dtype=float)

    def insert_step_into_history(self, timestamp, value):
        self.soc_history.loc[timestamp, 'soc_at_timestamp'] = value

    def discharge(self, load: float) -> float:
        if self.state_of_charge * config.DISCHARGE_EFFICIENCY < load:
            energy_to_return = self.state_of_charge * config.DISCHARGE_EFFICIENCY
            self.state_of_charge = 0
            print('battery is empty')
        else:
            energy_to_return = load
            self.state_of_charge -= load / config.DISCHARGE_EFFICIENCY
            print(f'battery discharged: {load:.2f} kW, remaining: {self.state_of_charge:.2f} kW')
        return energy_to_return

    def charge(self, generation: float) -> float:
        overflow = 0
        if self.state_of_charge + generation * config.CHARGE_EFFICIENCY > self.capacity:
            remaining_internal_space = self.capacity - self.state_of_charge
            used_portion_of_generation = remaining_internal_space / config.CHARGE_EFFICIENCY
            overflow = generation - used_portion_of_generation
            self.state_of_charge = self.capacity
            print(f'battery full, overflow: {overflow:.2f}')
        else:
            self.state_of_charge += generation * config.CHARGE_EFFICIENCY
            print(f'battery charged with {generation:.2f} kW, up to: {self.state_of_charge:.2f} kW')
        return overflow

