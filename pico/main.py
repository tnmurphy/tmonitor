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

lut_full_update = [
    0x80,
    0x60,
    0x40,
    0x00,
    0x00,
    0x00,
    0x00,  # LUT0: BB:     VS 0 ~7
    0x10,
    0x60,
    0x20,
    0x00,
    0x00,
    0x00,
    0x00,  # LUT1: BW:     VS 0 ~7
    0x80,
    0x60,
    0x40,
    0x00,
    0x00,
    0x00,
    0x00,  # LUT2: WB:     VS 0 ~7
    0x10,
    0x60,
    0x20,
    0x00,
    0x00,
    0x00,
    0x00,  # LUT3: WW:     VS 0 ~7
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,  # LUT4: VCOM:   VS 0 ~7
    0x03,
    0x03,
    0x00,
    0x00,
    0x02,  # TP0 A~D RP0
    0x09,
    0x09,
    0x00,
    0x00,
    0x02,  # TP1 A~D RP1
    0x03,
    0x03,
    0x00,
    0x00,
    0x02,  # TP2 A~D RP2
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,  # TP3 A~D RP3
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,  # TP4 A~D RP4
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,  # TP5 A~D RP5
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,  # TP6 A~D RP6
    0x15,
    0x41,
    0xA8,
    0x32,
    0x30,
    0x0A,
]

lut_partial_update = [  # 20 bytes
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,  # LUT0: BB:     VS 0 ~7
    0x80,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,  # LUT1: BW:     VS 0 ~7
    0x40,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,  # LUT2: WB:     VS 0 ~7
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,  # LUT3: WW:     VS 0 ~7
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,  # LUT4: VCOM:   VS 0 ~7
    0x0A,
    0x00,
    0x00,
    0x00,
    0x00,  # TP0 A~D RP0
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,  # TP1 A~D RP1
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,  # TP2 A~D RP2
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,  # TP3 A~D RP3
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,  # TP4 A~D RP4
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,  # TP5 A~D RP5
    0x00,
    0x00,
    0x00,
    0x00,
    0x00,  # TP6 A~D RP6
    0x15,
    0x41,
    0xA8,
    0x32,
    0x30,
    0x0A,
]

EPD_WIDTH = 128  # 122
EPD_HEIGHT = 250

RST_PIN = 12
DC_PIN = 8
CS_PIN = 9
BUSY_PIN = 13

FULL_UPDATE = 0
PART_UPDATE = 1


class EPD_2in13(framebuf.FrameBuffer):
    def __init__(self):
        self.led = Pin("LED", Pin.OUT)
        self.reset_pin = Pin(RST_PIN, Pin.OUT)
        self.dc_pin = Pin(DC_PIN, Pin.OUT)
        self.busy_pin = Pin(BUSY_PIN, Pin.IN, Pin.PULL_UP)
        
        self.cs_pin = Pin(CS_PIN, Pin.OUT)
        self.width = EPD_WIDTH
        self.height = EPD_HEIGHT

        self.full_lut = lut_full_update
        self.partial_lut = lut_partial_update

        self.full_update = FULL_UPDATE
        self.part_update = PART_UPDATE

        #self.ReadBusy()

        self.spi = SPI(1)
        self.spi.init(baudrate=4000_000)

        self.buffer = bytearray(self.height * self.width // 8)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_HLSB)
        self.init(FULL_UPDATE)

    def digital_write(self, pin, value):
        pin.value(value)

    def digital_read(self, pin):
        return pin.value()

    def delay_ms(self, delaytime):
        utime.sleep(delaytime / 1000.0)

    def spi_writebyte(self, data):
        self.spi.write(bytearray(data))

    def module_exit(self):
        self.digital_write(self.reset_pin, 0)

    # Hardware reset
    def reset(self):
        self.digital_write(self.reset_pin, 1)
        self.delay_ms(50)
        self.digital_write(self.reset_pin, 0)
        self.delay_ms(2)
        self.digital_write(self.reset_pin, 1)
        self.delay_ms(50)

    def send_command(self, command):
        self.digital_write(self.dc_pin, 0)
        self.digital_write(self.cs_pin, 0)
        self.spi_writebyte([command])
        self.digital_write(self.cs_pin, 1)

    def send_data(self, data):
        self.digital_write(self.dc_pin, 1)
        self.digital_write(self.cs_pin, 0)
        self.spi_writebyte([data])
        self.digital_write(self.cs_pin, 1)

    def ReadBusy(self):
        while self.digital_read(self.busy_pin) == 1:  # 0: idle, 1: busy
            self.delay_ms(10)

    def TurnOnDisplay(self):
        self.send_command(0x22)
        self.send_data(0xC7)
        self.send_command(0x20)
        self.ReadBusy()

    def TurnOnDisplayPart(self):
        self.send_command(0x22)
        self.send_data(0x0C)
        self.send_command(0x20)
        self.ReadBusy()

    def init(self, update):
        # print('init')
        self.reset()
        if update == self.full_update:
            self.ReadBusy()
            self.send_command(0x12)  # soft reset
            self.ReadBusy()

            self.send_command(0x74)  # set analog block control
            self.send_data(0x54)
            self.send_command(0x7E)  # set digital block control
            self.send_data(0x3B)

            self.send_command(0x01)  # Driver output control
            self.send_data(0x27)
            self.send_data(0x01)
            self.send_data(0x01)

            self.send_command(0x11)  # data entry mode
            self.send_data(0x01)

            self.send_command(0x44)  # set Ram-X address start/end position
            self.send_data(0x00)
            self.send_data(0x0F)  # 0x0C-->(15+1)*8=128

            self.send_command(0x45)  # set Ram-Y address start/end position
            self.send_data(0x27)  # 0xF9-->(249+1)=250
            self.send_data(0x01)
            self.send_data(0x2E)
            self.send_data(0x00)

            self.send_command(0x3C)  # BorderWavefrom
            self.send_data(0x03)

            self.send_command(0x2C)  # VCOM Voltage
            self.send_data(0x55)  #

            self.send_command(0x03)
            self.send_data(self.full_lut[70])

            self.send_command(0x04)  #
            self.send_data(self.full_lut[71])
            self.send_data(self.full_lut[72])
            self.send_data(self.full_lut[73])

            self.send_command(0x3A)  # Dummy Line
            self.send_data(self.full_lut[74])
            self.send_command(0x3B)  # Gate time
            self.send_data(self.full_lut[75])

            self.send_command(0x32)
            for count in range(70):
                self.send_data(self.full_lut[count])

            self.send_command(0x4E)  # set RAM x address count to 0
            self.send_data(0x00)
            self.send_command(0x4F)  # set RAM y address count to 0X127
            self.send_data(0x0)
            self.send_data(0x00)
            self.ReadBusy()
        else:
            self.send_command(0x2C)  # VCOM Voltage
            self.send_data(0x26)

            self.ReadBusy()

            self.send_command(0x32)
            for count in range(70):
                self.send_data(self.partial_lut[count])

            self.send_command(0x37)
            self.send_data(0x00)
            self.send_data(0x00)
            self.send_data(0x00)
            self.send_data(0x00)
            self.send_data(0x40)
            self.send_data(0x00)
            self.send_data(0x00)

            self.send_command(0x22)
            self.send_data(0xC0)
            self.send_command(0x20)
            self.ReadBusy()

            self.send_command(0x3C)  # BorderWavefrom
            self.send_data(0x01)
        return 0

    def display(self, image):
        self.send_command(0x24)
        for j in range(0, self.height):
            for i in range(0, int(self.width / 8)):
                self.send_data(image[i + j * int(self.width / 8)])
        self.TurnOnDisplay()

    def displayPartial(self, image):
        self.send_command(0x24)
        for j in range(0, self.height):
            for i in range(0, int(self.width / 8)):
                self.send_data(image[i + j * int(self.width / 8)])

        self.send_command(0x26)
        for j in range(0, self.height):
            for i in range(0, int(self.width / 8)):
                self.send_data(~image[i + j * int(self.width / 8)])
        self.TurnOnDisplayPart()

    def displayPartBaseImage(self, image):
        self.send_command(0x24)
        for j in range(0, self.height):
            for i in range(0, int(self.width / 8)):
                self.send_data(image[i + j * int(self.width / 8)])

        self.send_command(0x26)
        for j in range(0, self.height):
            for i in range(0, int(self.width / 8)):
                self.send_data(image[i + j * int(self.width / 8)])
        self.TurnOnDisplay()

    def Clear(self, color):
        self.send_command(0x24)
        for j in range(0, self.height):
            for i in range(0, int(self.width / 8)):
                self.send_data(color)
        self.send_command(0x26)
        for j in range(0, self.height):
            for i in range(0, int(self.width / 8)):
                self.send_data(color)

        self.TurnOnDisplay()

    def sleep(self):
        self.send_command(0x10)  # enter deep sleep
        self.send_data(0x03)
        self.delay_ms(2000)
        self.module_exit()


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
    last_t: Reading = Reading(0)
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

        if t.value < cls.threshold and cls.last_t.value > cls.threshold:
            cls.dipped_t = t
        cls.last_t = t
        cls.last_uploaded = False

    @classmethod
    def show_temp(cls, epd):
        epd.init(epd.full_update)
        epd.delay_ms(100)
        epd.Clear(0xFF)
        xpos = 2
        ypos = 10
        epd.fill(0xFF)

        # epd.delay_ms(100)
        text = [
            f"Temp: {cls.last_t.value:.4} *C",
            f" on {cls.last_t.date_string}",
            f" at {cls.last_t.time_string}",
            f"Min:  {cls.min_t.value:.4} *C",
            f" on {cls.min_t.date_string}",
            f" at {cls.min_t.time_string}",
            f"Max:  {cls.max_t.value:.4} *C",
            f" on {cls.max_t.date_string}",
            f" at {cls.max_t.time_string}",
            f"Dipped < {cls.threshold:.4} *C",
            f" on {cls.dipped_t.date_string}",
            f" at {cls.dipped_t.time_string}",
        ]
        for t in text:
            epd.text(t, xpos, ypos, 0x00)
            ypos += 20
        # print("{:.4} Deg.C".format(t))
        epd.display(epd.buffer)
        epd.delay_ms(1000)


def read_battery_level():
    p = ADC(0)
    level = p.read_u16()
    return level


async def connect(wlan):
    """Connect to wireless network"""

    wlan.active(True)
    wlan.connect(secrets.wifi_ssid, secrets.wifi_password)
    while not wlan.isconnected():
        await uasyncio.sleep_ms(500)
        # print(f"wlan status: {wlan.status()}")
    ip = wlan.ifconfig()[0]
    return ip


def disconnect(wlan):
    wlan.disconnect()
    wlan.active(False)


async def show_temp(led: Pin, period_ms: int):
    print("show_temp: started")
    epd = EPD_2in13()
    epd.delay_ms(20)
    blink(led, 2)  # temperature shower initialised

    while True:
        print("show_temp: displaying\n")
        TempStats.show_temp(epd)
        await uasyncio.sleep_ms(period_ms)


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
                blink(led)  # network connection
                localtime = utime.time()
                print(f"uploader: connected to lan as {ip=}")
                print(f"uploader: time {localtime}")

                rj = """[{
                "sensor": "%s",
                "unit": "C",
                "value": %f,
                "recorded_timestamp": %d
                 }]""" % (
                    machine_id + "_temp",
                    TempStats.last_t.value,
                    int(TempStats.last_t.time_secs),
                )
                print(f"uploader: sending {rj}")
                response = requests.post(secrets.backend_url + "/sense", data=rj)
                print(f"uploader: response: {response.status_code}")
                if response.status_code == 200:
                    TempStats.last_uploaded = True
                    if m := time_re.match(response.text):
                        # Set the local clock to match the remote one.

                        servertime = int(m.groups()[1])
                        time_delta = localtime - servertime
                        
                        # don't set the time repeatedly, only
                        # if there has been noticable drift
                        if time_delta < -10 or time_delta > 10:
                            dt = datetime.fromtimestamp(servertime)
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
        print(f"uploader: sleeping for {post_period}ms starting {localtime}, wake at {localtime+post_period/1000}")
        await uasyncio.sleep_ms(post_period)


async def main(led: Pin, debug: bool):
    if debug:
        monitor_period = 20 * 1000
        upload_period = 30 * 1000
    else:
        monitor_period = int(4.9 * 60 * 1000)
        upload_period = 5 * 60 * 1000
    tasks = [
        uasyncio.create_task(monitor_temp(monitor_period)),
        uasyncio.create_task(uploader(led, upload_period)),
        #uasyncio.create_task(show_temp(led, monitor_period)),
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
