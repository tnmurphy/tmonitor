## Monitor ##

**Author: Timothy N Murphy <tnmurphy@gmail.com>**


## Summary ##

Yet another way to keep track of temperature and other data. In my case this is a temperature sensor in a greenhouse.  The aim is to know when its getting too cold so that I can either bring the plants inside or switch on some kind of heater. 

"Probes" upload temperature (or other data) to a backend through an HTTP POST. The backend has another endpoint for querying said data. 

The backend is just a simple FastAPI program in python that receives temperatures.  Probes can be anything but an example one for a Raspberry Pico 2W is included. Wif is the communication method at the moment although it might be worth exploring Bluetooth. The current probe assumes that an eink display is connected to the PICO and displays current data on the screen but this can easily be disabled if one doesn't have it. 

## Making the backend run ##
The backend needs python along with some dependencies. I've included a .service file so that systemd can run it from a
home directory although the username and homedir might need to be altered.  The service runs as the pi user. In general
it's not safe to expose this to the internet at the moment so it should run in the local network. 

The following instructions are for a raspberry pi but will probably work for almost any linux device with python3 and sqllite installed.

* Checkout the module from github
* fetch all the dependencies and create a virtual environment
* initialise a database
* edit the tmonitor.service file to reflect the user you want to run as
* copy the service file into /etc and start the service


```
git clone https://github.com/tnmurphy/tmonitor && 
(cd tmonitor && {

python3 pv run database.py  && # configure the database and also create the venv and install dependencies
sudo  cp tmonitor.service  && /etc/systemd/system/tmonitor.service
sudo systemctl enable tmonitor 

})
```

## The Pico Probe ##
To install this you'll need a Raspberry Pi Pico and the IDE called Thonny.   The pico should have a recent version of Micropython and Thonny should be used to install some packages on it:
 
* base64
* datetime
* picozero
* micropython-framebuf

The probe can be found in "pico/main.py" and as with all of them you can save this on the Pico as "main.py" to make it run on bootup.

A file named "secrets.py" must also be saved to the PICO in the same location as "main.py". This will hold the WIFI ssid and password and the URL of the backend.  DON'T check this into git :-).

Example of secrets.py
```
wifi_ssid = "my_iot_net"
wifi_password = "blah_blah_blah"
backend_url = "http://myraspberrypi.local:5000"

```

The probe uses an asynchronous event loop with several tasks - the display task is disabled by default since you might not have an eink display.  This can be changed in the main() function as can the reporting period and other things. There is a debug mode which reports and checks temperature more frequently - setting debug=True in the call to main() will change this.

It's wise to try the code out in Thonny with the backend server started before trying to run the Pico disconnected. 

