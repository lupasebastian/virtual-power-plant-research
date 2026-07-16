import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import matplotlib.dates as mdates

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

    def insert_step_into_history(self, timestamp, value, overflow):
        self.soc_history.loc[timestamp, ['soc_at_timestamp', 'overflow']] = [value, overflow]

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

def plot_daily_results(day, index, hourly_output, hourly_overflows, hourly_targets, hourly_soc):
    fig, ax1 = plt.subplots(figsize=(14, 7), dpi=100)
    ax2 = ax1.twinx()

    x_positions = np.arange(len(index))
    bar_width = 0.35

    ax1.bar(x_positions - bar_width / 2, hourly_output, bar_width, label='Predicted AC Output (kW)', color='#F1C40F',
            alpha=0.8)
    ax1.bar(x_positions + bar_width / 2, hourly_overflows, bar_width, label='Wasted Grid Overflow (kW)',
            color='#9B59B6',
            alpha=0.8)
    ax1.plot(x_positions, hourly_targets, color='#2C3E50', linewidth=2.5, marker='s', markersize=4,
             label='Hourly Targets / Demand (kW)', zorder=5)

    ax2.plot(x_positions, hourly_soc, color='#2980B9', linewidth=2.5, linestyle='--', marker='o', markersize=5,
             label='State of Charge (kWh)')
    ax2.axhline(y=5.0, color='#2980B9', linestyle=':', alpha=0.4, label='Max Battery Cap (5.0 kWh)')

    ax1.set_xlabel(f'Hour of Day ({day})', fontsize=11, labelpad=10)
    ax1.set_ylabel('Instantaneous Power Rates (kW)', fontsize=11, color='#2C3E50')
    ax2.set_ylabel('Stored Battery Energy (kWh)', fontsize=11, color='#2980B9')

    ax1.tick_params(axis='y', labelcolor='#2C3E50')
    ax2.tick_params(axis='y', labelcolor='#2980B9')

    ax1.set_xticks(x_positions)
    ax1.set_xticklabels([t.strftime('%H:%M') for t in index], rotation=45)
    ax1.grid(axis='y', linestyle=':', alpha=0.5)
    ax1.set_ylim(0, 8.0)  # Gives breathing room for the header legend
    ax2.set_ylim(0, 5.5)

    plt.title('Combined Solar System Simulation Overview (Opole)', fontsize=13, fontweight='bold', pad=15)

    handles_1, labels_1 = ax1.get_legend_handles_labels()
    handles_2, labels_2 = ax2.get_legend_handles_labels()
    ax1.legend(handles_1 + handles_2, labels_1 + labels_2, loc='upper left', framealpha=0.95)

    plt.tight_layout()
    plt.show()


def plot_monthly_results(hourly_output, hourly_overflows, hourly_targets, hourly_soc):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 9), sharex=True, dpi=100)

    ax1.fill_between(hourly_output.index, hourly_output, color='#F1C40F', alpha=0.3, label='Predicted AC Output (kW)')
    ax1.plot(hourly_output.index, hourly_output, color='#D4AC0D', linewidth=1, alpha=0.6)

    ax1.fill_between(hourly_overflows.index, hourly_overflows, color='#9B59B6', alpha=0.3, label='Wasted Grid Overflow (kW)')
    ax1.plot(hourly_overflows.index, hourly_overflows, color='#8E44AD', linewidth=1, alpha=0.5)

    ax1.plot(hourly_targets.index, hourly_targets, color='#2C3E50', linewidth=1.5, label='Hourly Demand Target (kW)', zorder=5)

    ax1.set_ylabel('Power Flow Rates (kW)', fontsize=11)
    ax1.set_title('Monthly Energy Performance Overview (Opole)', fontsize=14, fontweight='bold', pad=10)
    ax1.grid(True, linestyle=':', alpha=0.4)
    ax1.legend(loc='upper left', framealpha=0.95)

    ax2.plot(hourly_soc.index, hourly_soc, color='#2980B9', linewidth=2, label='State of Charge (kWh)')
    ax2.fill_between(hourly_soc.index, hourly_soc, color='#2980B9', alpha=0.1)
    ax2.axhline(y=5.0, color='#C0392B', linestyle=':', linewidth=1.5, alpha=0.7, label='Max Storage Limit (5.0 kWh)')

    ax2.set_ylabel('Battery Storage State (kWh)', fontsize=11)
    ax2.set_xlabel('Date', fontsize=11, labelpad=10)
    ax2.grid(True, linestyle=':', alpha=0.4)
    ax2.legend(loc='upper left', framealpha=0.95)
    ax2.set_ylim(0, 5.5)

    ax2.xaxis.set_major_locator(mdates.DayLocator(interval=3))
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax2.xaxis.set_minor_locator(mdates.DayLocator(interval=1))

    plt.xticks(rotation=0, ha='center')

    plt.tight_layout()
    plt.show()