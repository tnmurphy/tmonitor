"""
Temperature probe for Raspberry Pi Pico 2W


Copyright (c) Timothy Norman Murphy <tnmurphy@gmail.com>
"""

from machine import Pin, SPI, ADC, RTC, unique_id
from datetime import datetime
import framebuf
import utime
import network
from picozero import pico_temp_sensor, pico_led
import uasyncio
import urequests as requests
import re
import secrets
import base64
import gc


def get_temp():
    temp_sensor = ADC(4)
    temperature = temp_sensor.read_u16()
    to_volts = 3.3 / 65535
    temperature = temperature * to_volts
    celsius_degrees = 27 - (temperature - 0.706) / 0.001721
    return celsius_degrees


def time_date(time_secs):
    time_t = utime.localtime(time_secs)
    date_string = "{}-{}-{}".format(time_t[0], time_t[1], time_t[2])

    time_string = "{:02d}:{:02d}:{:02d}".format(time_t[3], time_t[4], time_t[5])
    return time_string, date_string


class Reading:
    """A sensor reading - basically a value and a time."""

    def __init__(self, value: float, time_secs=None):
        self.value = value
        if time_secs is None:
            self.time_secs = utime.time()
        self.time_string, self.date_string = time_date(self.time_secs)

    def __lt__(self, other):
        return self.value < other.value

    def __gt__(self, other: "Reading") -> bool:
        return self.value > other.value

    @classmethod
    def get(cls) -> "Reading":
        return cls(get_temp())


class TempStats:
    max_t: Reading = Reading(-1000)
    min_t: Reading = Reading(1000)
    last_t: list[Reading] = [Reading(0)]
    last_uploaded: bool = False
    dipped_t: Reading = Reading(0)
    threshold: float = 5.0

    @classmethod
    def check_temp(cls) -> str:
        t = Reading.get()

        if cls.max_t < t:
            cls.max_t = t
        if cls.min_t > t:
            cls.min_t = t

        if t.value < cls.threshold and cls.last_t[-1].value > cls.threshold:
            cls.dipped_t = t
        cls.last_t.append(t)
        cls.last_uploaded = False

def read_battery_level():
    p = ADC(0)
    level = p.read_u16()
    return level


async def connect(wlan):
    """Connect to wireless network"""

    wlan.active(True)
    wlan.connect(secrets.wifi_ssid, secrets.wifi_password)
    retries = 15
    while not wlan.isconnected():
        await uasyncio.sleep_ms(500)
        retries -= 1
        if retries <= 0:
            return None
        # print(f"wlan status: {wlan.status()}")
    ip = wlan.ifconfig()[0]
    
    return ip


def disconnect(wlan):
    wlan.disconnect()
    wlan.active(False)


async def monitor_temp(period_ms: int):
    print("monitor: started")
    while True:
        localtime = utime.time()
        print(f"monitor: measuring temperature at {localtime}\n")
        TempStats.check_temp()
        await uasyncio.sleep_ms(period_ms)


async def uploader(led: Pin, post_period: int):
    print("uploader: started")
    wlan = network.WLAN(network.STA_IF)
    time_re = re.compile('"current_timestamp" *: *([0-9]+)')
    machine_id = base64.urlsafe_b64encode(unique_id()).decode("utf-8")[:-1]
    print(f"Machine ID: {machine_id}")
    rtc = RTC()

    while True:
        print(f"uploader: last set of stats uploaded: {TempStats.last_uploaded}")
        if not TempStats.last_uploaded:
            try:
                ip = await connect(wlan)
                if ip is None:
                    raise Exception("connect failure after retries")
                blink(led)  # network connection
                localtime = utime.time()
                print(f"uploader: connected to lan as {ip=}")
                print(f"uploader: time {localtime}")

                response_list = []
                for last_t in TempStats.last_t:
                    rj = """{
                    "sensor": "%s",
                    "unit": "C",
                    "value": %f,
                    "recorded_timestamp": %d
                     }""" % (
                        machine_id + "_temp",
                        last_t.value,
                        int(last_t.time_secs),
                    )
                    response_list.append(rj)
                response_body = "[" + ",".join(response_list) + "]"
                print(f"uploader: sending {response_body}")
                response = requests.post(
                    secrets.backend_url + "/sense", data=response_body
                )
                print(f"uploader: response: {response.status_code}")

                if response.status_code == 200:
                    TempStats.last_uploaded = True
                    TempStats.last_t = []
                    if m := time_re.match(response.text):
                        # Set the local clock to match the remote one.

                        servertime = int(m.groups()[1])
                        time_delta = localtime - servertime

                        # don't set the time repeatedly, only
                        # if there has been noticable drift
                        if time_delta < -10 or time_delta > 10:
                            dt = datetime.fromtimestamp(servertime)
                            print(f"uploader: correcting time to {dt}")
                            rtc.datetime(dt.timetuple())
                # await uasyncio.sleep_ms(1000)
                blink(led, 4)
                print("uploader: disconnecting")
                disconnect(wlan)
            except Exception as e:
                print(f"uploader: exception: {type(e)} {str(e)}")
                if type(e) is SyntaxError:  # for syntax errors we do want to crash
                    raise e
        else:
            print("uploader: nothing new to upload")
        localtime = utime.time()
        print(
            f"uploader: sleeping for {post_period}ms starting {localtime}, wake at {localtime+post_period/1000}"
        )
        print("uploader: heap memory free before collection:", gc.mem_free())
        print("uploader: heap memory used:", gc.mem_alloc())
        gc.collect()
        print("uploader: heap memory free after collection:", gc.mem_free())
        print("uploader: heap memory used:", gc.mem_alloc())
        await uasyncio.sleep_ms(post_period)


async def main(led: Pin, debug: bool):
    if debug:
        monitor_period = 20 * 1000
        upload_period = 30 * 1000
    else:
        monitor_period = 5 * 60 * 1000
        upload_period = 5 * 60 * 1000
    tasks = [
        uasyncio.create_task(monitor_temp(monitor_period)),
        uasyncio.create_task(uploader(led, upload_period)),
        # uasyncio.create_task(show_temp(led, monitor_period)),
    ]
    await uasyncio.gather(*tasks)  # will never happen, as things stand.
    print("main: gathered tasks. Stopping")


def blink(led, count=1):
    for i in range(0, count):
        led.on()
        utime.sleep(0.3)
        led.off()
        utime.sleep(0.6)
    utime.sleep(1)


if __name__ == "__main__":
    led = Pin("LED", Pin.OUT)
    blink(led)
    print("Start")
    utime.sleep(2)
    uasyncio.run(main(led, debug=False))
    # print(f"lightsleeping {lightsleep_mins}")
    # machine.lightsleep(lightsleep_mins*60*1000)GG
