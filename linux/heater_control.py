#!/usr/bin/env python3
"""
Run the heater for a few minutes and ensure it's off for
the same time.
"""
from gpiozero import LED
from time import sleep
import sys
import temp

def sleep_print(period: int, log_period: int, status: str):
    counter = 0
    print(f"heater_control: sleeping for {period}s")
    while counter < period:
        sleep(log_period)
        counter += log_period
        sys.stdout.write(f"heater_control: {status} for {counter} of {period}s\n")
         

def run_heater(seconds: int = 300, seconds_off: int = 300):
    led=LED(22)
    print(f"heater_control: pin: {led.value}")
    print(f"heater_control: Active_high: {led.active_high}")
    assert seconds_off > 0
    assert seconds_off > seconds
    try:
        led.on()
        print(f"heater_control: switching on: {led.value}")
        sleep_print(seconds, 60, "on") # five minutes.
    finally:
        led.close()
        print(f"heater_control: switching off: {led}")
        sleep_print(seconds_off, 60, "off") # force it to be off for a set period

def heat_loop(low_temp: float, heater_on_secs: int, heater_off_secs: int):
    therm = temp.TemperatureReader()
    low_temp_counter = 0
    sys.stdout.write(f"heater_control: heat_loop mode to maintain > {low_temp} deg. C\n")
    while True:
        sleep(60)
        t = therm.read()
        if t < low_temp:
            low_temp_counter += 1
            sys.stdout.write(f"heater_control: low temperature {temp}\n")
            if low_temp_counter == 3: # fire up if we measure a low temperature 3 times
                sys.stdout.write(f"heater_control: low temperature seen 3 times: running heater for {heater_on_secs}s\n")
                run_heater(heater_on_secs, heater_off_secs)
                low_temp_counter = 0
        else:
            sys.stdout.write(f"heater_control: temperature ok: {t} >= {low_temp}\n")
            low_temp_counter = 0

if __name__ == "__main__":

    runtime=300
    if len(sys.argv) > 1:
        if sys.argv[1] == "server":
            # bounce the heat up if it goes below 6
            heat_loop(6,300,45*60)
        else:
            runtime = int(sys.argv[1])
            run_heater(runtime)
