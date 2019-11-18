from os import path
import functools
import gateway_addon
import signal
import sys
import time

sys.path.append(path.join(path.dirname(path.abspath(__file__)), 'lib'))

try:
    from btlewrap import available_backends, BluepyBackend, GatttoolBackend, PygattBackend

    from miflora.miflora_poller import MiFloraPoller, \
        MI_CONDUCTIVITY, MI_MOISTURE, MI_LIGHT, MI_TEMPERATURE, MI_BATTERY
    from miflora import miflora_scanner    
    
    
    #from miflora.miflora_poller import MiFloraPoller
    #from miflora import miflora_scanner
    #from btlewrap.bluepy import BluepyBackend
    
    #from miflora import miflora_scanner, BluepyBackend
    #from miflora.miflora_poller import MiFloraPoller
    #from btlewrap.bluepy import BluepyBackend
except Exception as ex:
    print("Error loading requirements: " + str(ex))

backend = BluepyBackend
devices = miflora_scanner.scan(backend, 10)
#print('Found {} devices:'.format(len(devices)))
for device in devices:
    print('{}'.format(device))