"""Xiaomi Miflora adapter for Mozilla WebThings Gateway."""

import os
from os import path
import sys

sys.path.append(path.join(path.dirname(path.abspath(__file__)), 'lib'))

import json
import threading
import subprocess

import time
from time import sleep

from gateway_addon import Adapter, Database
from .xiaomi_miflora_device import MifloraDevice

try:
    from btlewrap import available_backends, BluepyBackend, GatttoolBackend, PygattBackend

    from miflora.miflora_poller import MiFloraPoller, \
        MI_CONDUCTIVITY, MI_MOISTURE, MI_LIGHT, MI_TEMPERATURE, MI_BATTERY
    from miflora import miflora_scanner
except Exception as ex:
    print("Error loading requirements: " + str(ex))




__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

_CONFIG_PATHS = [
    os.path.join(os.path.expanduser('~'), '.mozilla-iot', 'config'),
]

if 'MOZIOT_HOME' in os.environ:
    _CONFIG_PATHS.insert(0, os.path.join(os.environ['MOZIOT_HOME'], 'config'))



class XiaomiMifloraAdapter(Adapter):
    """Adapter for Xiaomi Miflora"""

    def __init__(self, verbose=False):
        """
        Initialize the object.

        verbose -- whether or not to enable verbose logging
        """
        print("Initialising Xiaomi Miflora adapter")
        self.pairing = False
        self.name = self.__class__.__name__
        Adapter.__init__(self, 'xiaomi-miflora', 'xiaomi-miflora', verbose=verbose)
        #print("Adapter ID = " + self.get_id())

        for path in _CONFIG_PATHS:
            if os.path.isdir(path):
                self.persistence_file_path = os.path.join(
                    path,
                    'xiaomi-miflora-persistence.json'
                )
        
        self.add_on_path = os.path.join(os.path.expanduser('~'), '.mozilla-iot', 'addons','xiaomi-miflora')
        #print("self.add_on_path = " + str(self.add_on_path))
        
        #self.metric = True
        #self.temperature_unit = 'degree celsius'
        self.DEBUG = False
        self.initial_scan_done = False
        self.running = True
        
        self.macs = set()
        self.stragglers = set()
        
        self.busy = False # Whether a poll is already in progress.
        
        self.last_update_all_time = 0 # When the last full polling of all devices was done
        self.last_scan_time = 0 # When the last full scan for new devices was done
        
        self.polling_interval_seconds = 24 * 60 * 60 # By default the add-on polls every 24 hours.
        
        # Load settings
        try:
            self.add_from_config()
        except Exception as ex:
            print("Error loading config (and initialising BluetoothMiflora library?): " + str(ex))

        # Do an initial scan to populate the devices
        done = self.start_scan()

        # Start the clock that checks if a new full poll should be performed.
        if self.DEBUG:
            print("Starting the internal clock")
        try:
            t = threading.Thread(target=self.clock)
            t.daemon = True
            t.start()
        except:
            print("Error starting the clock thread")                    
        


    def clock(self):
        """ Runs every minute and updates which devices are still connected """
        if self.DEBUG:
            print("clock thread init")
        while self.running:
            time.sleep(60)
            if self.DEBUG:
                print("CLOCK TICK")
            self.update_all()
                


    def unload(self):
        print("Shutting down Miflora adapter")
        self.running = False



    def remove_thing(self, device_id):
        if self.DEBUG:
            print("Removing MiFlora device: " + str(device_id))
        
        try:
            obj = self.get_device(device_id)        
            self.handle_device_removed(obj)                     # Remove from device dictionary
            print("Removed device")
        except Exception as ex:
            print("Error removing thing: " + str(ex))



    def add_from_config(self):
        """Attempt to add all configured devices."""
        try:
            database = Database('xiaomi-miflora')
            if not database.open():
                return

            config = database.load_config()
            database.close()
        except:
            print("Error! Failed to open settings database.")

        if not config:
            print("Error loading config from database")
            return
        
        
        # Debug
        try:
            if 'Debugging' in config:
                self.DEBUG = bool(config['Debugging'])
                if self.DEBUG:
                    print("-Debug preference is present in the config data.")
        except Exception as ex:
            print("Debug preference error:" + str(ex))
            
        
        # Polling interval
        try:
            if 'Polling interval' in config:
                if self.DEBUG:
                    print("-Polling interval preference is present in the config data.")
                if int(config['Polling interval']) != 0:
                    self.polling_interval_seconds = int(config['Polling interval']) * 60 * 60
            else:
                if self.DEBUG:
                    print("-Polling interval was not in config, will stay with default of 24h.")
        except Exception as ex:
            print("Polling interval preference error:" + str(ex))
            
        return




    def start_pairing(self, timeout):
        """
        Start the pairing process. This starts when the user presses the + button on the things page.

        timeout -- Timeout in seconds at which to quit pairing
        """
        
        if self.DEBUG:
            print("PAIRING INITIATED")
        
        try:
            done = self.start_scan()
        except Exception as ex:
            print("BLE Scan failed: " + str(ex))
        
        return



#    def cancel_pairing(self):
#        """Cancel the pairing process."""
#        print("Cancelling of pairing has been called")
#        self.pairing = False
        
        

    def start_scan(self):
        
        # Rate limiting to once a minute at most. A scan takes 10 seconds, but polling all the devices also takes quite some time.
        if time.time() - self.last_scan_time > 60 and self.busy == False:
            #self.busy = True
            self.last_scan_time = time.time()
        
            try:
                
                new_devices = []
                command = "sudo python3 " + os.path.join(self.add_on_path,'scan.py')
                for line in run_command(command).splitlines():
                    #if self.DEBUG:
                    #    print(line)
                    if line.startswith( 'C4:7C:8D' ): # All MiFlora devices start with this
                        try:
                            if line not in self.macs:
                                self.macs.add(line)
                                self.add_a_flora(line)
                                new_devices.append(line)
                        except Exception as ex:
                            print("Error polling MiFlora device: " + str(ex))

                # Do a quick scan of the newly found devices

                for mac in new_devices:  
                    try:
                        if self.DEBUG:
                            print("Polling newly found device " + str(mac))
                        done = self.poll_a_flora(mac)
                        if self.DEBUG:
                            print("sleeping between polls...")
                        sleep(5)
                    except Exception as ex:
                        print("Error polling device: " + str(ex))
        
                self.initial_scan_done = True;
                if self.DEBUG:
                    print("Done scanning for new MiFlora devices")

                

            except Exception as ex:
                print("Error running BLUE scan: " + str(ex))
        
            #self.busy = False
        
        return True
        
        
        
    def update_all(self):
        
        self.stragglers.clear() # Clears the list of device that didn't send any data
        
        if time.time() - self.last_update_all_time > self.polling_interval_seconds and self.initial_scan_done and self.busy == False:
            self.busy = True
            self.last_update_all_time = time.time()
        
            print("Now polling all MiFlora devices")
            for mac in self.macs:  
                try:
                    done = self.poll_a_flora(mac)
                    if self.DEBUG:
                        print("sleeping...")
                    sleep(5)
                except Exception as ex:
                    print("Error polling device: " + str(ex))
            
            # Wait 5 minutes, then try again for the devices that didn't connect properly the first time.
            if len(self.stragglers) > 0:
                sleep(300) 
                for mac in self.stragglers:
                    print("Trying again to connect to " + str(mac))
                    try:
                        done = self.poll_a_flora(mac)
                        if self.DEBUG:
                            print("sleeping...")
                        sleep(10)
                    except Exception as ex:
                        print("Error polling device: " + str(ex))
            self.busy = False
    

    def add_a_flora(self,mac):
        try:
            name = 'xiaomi-miflora-{}'.format(mac)
            if self.DEBUG:
                print("")
                print("-creating: " + str(name))
            
            # We create the device object
            device = MifloraDevice(self, mac)
            
            # Finally, now that the device is complete, we present it to the Gateway.
            self.handle_device_added(device)
            print("Added MiFlora device: " + str(mac))
        except Exception as ex:
            print("Error trying to add new MiFlora device: " + str(ex))


    def poll_a_flora(self,mac):
        
        if self.busy == False:
            self.busy = True
        
            print("Polling MiFlora device: " + str(mac))
        
            name = 'xiaomi-miflora-{}'.format(mac)

            try:
                targetDevice = self.get_device(name)
                if str(targetDevice) != 'None':
                    if self.DEBUG:
                        print("Target device existed")
                    
            
                    updated_values = {}
                    poller = MiFloraPoller(mac, BluepyBackend)
            
                    # Get values from MiFlora
                    if self.DEBUG:
                        print("Getting data from Mi Flora")
                    try:
                        if self.DEBUG: 
                            print("FW: {}".format(poller.firmware_version()))
                            print("Name: {}".format(poller.name()))
                    except:
                        print("Couldn't get firmware and name")
            
                    try:
                        updated_values['temperature'] = poller.parameter_value(MI_TEMPERATURE)
                        print("Received temperature")
                    except:
                        print("Couldn't read temperature")
                    try:
                        updated_values['moisture'] = poller.parameter_value(MI_MOISTURE)
                        print("Received moisture level")
                    except:
                        print("Couldn't read moisture")
                    try:
                        updated_values['light'] = poller.parameter_value(MI_LIGHT)
                        print("Received light level")
                    except:
                        print("Couldn't read light") 
                    try:
                        updated_values['conductivity'] = poller.parameter_value(MI_CONDUCTIVITY)
                        print("Received conductivity")
                    except:
                        print("Couldn't read conductivity") 
                    try:
                        updated_values['battery'] = poller.parameter_value(MI_BATTERY)
                        print("Received battery level")
                    except:
                        print("Couldn't read battery level") 
            
            
                    # Updating thing properties
                    for property_name in updated_values:
                        targetProperty = targetDevice.find_property(property_name)
                        if targetProperty != None:
                            if self.DEBUG:
                                print("target " + str(property_name) + " property exists, updating")
                            targetProperty.update(updated_values[property_name])
                        else:
                            if self.DEBUG:
                                print("Strange, target property did not exist?")
            
            
                    # If no data was received, set the device to disconnected.
                    if len(updated_values) == 0:
                        if self.DEBUG:
                            print("Polling went poorly, no values received. Setting device to disconnected")
                        targetDevice.connected_notify(False)
                        self.stragglers.add(mac) # creates a list of devices that didn't connect propertly, and will get a second chance in 5 minutes.
                    else:
                        # If data was received, set the device to "connected".
                        targetDevice.connected_notify(True)
            
            except Exception as ex:
                print("Error polling Miflora device: "  + str(ex))
        
            self.busy = False
        
        return True # done


# Used to do the BLE scan, which requires sudo.
def run_command(cmd, timeout_seconds=60):
    try:
        
        p = subprocess.run(cmd, timeout=timeout_seconds, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, universal_newlines=True)

        if p.returncode == 0:
            return p.stdout  + '\n' + "Command success" 
        else:
            if p.stderr:
                return "Error: " + str(p.stderr)  + '\n' + "Command failed"

    except Exception as e:
        print("Error running subprocess: "  + str(e))
        