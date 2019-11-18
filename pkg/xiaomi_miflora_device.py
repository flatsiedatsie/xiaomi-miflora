"""Miflora adapter for Mozilla WebThings Gateway."""


import threading
import time

from gateway_addon import Device
from .xiaomi_miflora_property import MifloraProperty



class MifloraDevice(Device):
    """Miflora device type."""

    def __init__(self, adapter, name):
        """
        Initialize the object.

        adapter -- the Adapter managing this device
        _id -- ID of this device
        sketch_name -- The Miflora node name
        index -- index inside parent device
        """
        
        #self._id = "Miflora_" + str(_id)
        #_id = 'xiaomi-miflora-{}'.format(mac)   # was self._id = 'Miflora-{}'.format(_id)
        
        #print("Device init")
        Device.__init__(self, adapter, name)
        
        self.adapter = adapter
        self.id = name
        self.name = name
        self.title = name
        self.description = name
        
        self.properties = {}

        self._type.append('MultiLevelSensor')
        self.properties['moisture'] = MifloraProperty(
            self,
            'moisture',
            {
                '@type': 'LevelProperty',
                'label': 'Moisture',
                'minimum': 0,
                'maximum': 100,
                'multipleOf':1,
                'type': 'integer',
                'unit': 'percent',
                'readOnly': True,
            })
        #self._type.append('TemperatureSensor')
        self.properties['temperature'] = MifloraProperty(
            self,
            'temperature',
            {
                '@type': 'TemperatureProperty',
                'label': 'Temperature',
                'type': 'number',
                'unit': 'degree celsius',
                'multipleOf':.1,
                'readOnly': True,
            })
        self.properties['light'] = MifloraProperty(
            self,
            'light',
            {
                'label': 'Light',
                'multipleOf':1,
                'type': 'integer',
                'unit': 'Lux',
                'readOnly': True,
            })
        self.properties['conductivity'] = MifloraProperty(
            self,
            'conductivity',
            {
                'label': 'Conductivity',
                'multipleOf':1,
                'type': 'integer',
                'unit': 'µS/cm',
                'readOnly': True,
            })
        self.properties['battery'] = MifloraProperty(
            self,
            'battery',
            {
                'label': 'Battery',
                'minimum': 0,
                'maximum': 100,
                'multipleOf':1,
                'type': 'integer',
                'unit': 'percent',
                'readOnly': True,
            })
 
