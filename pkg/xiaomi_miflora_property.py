"""Miflora adapter for Mozilla WebThings Gateway."""

from gateway_addon import Property

class MifloraProperty(Property):
    """Miflora property type."""

    def __init__(self, device, name, description):
        """
        Initialize the object.

        device -- the Device this property belongs to
        name -- name of the property
        description -- description of the property, as a dictionary
        value -- current value of this property
        """
        try:
            if device.adapter.DEBUG:
                print("Property: initialising")
            Property.__init__(self, device, name, description)

            self.device = device
            self.name = name
            self.title = name
            self.description = description
            self.value = None

        except Exception as ex:
            print("inside adding property error: " + str(ex))


    def set_value(self, value):
        """
        Set the current value of the property.

        value -- the value to set
        """
        
        if self.device.adapter.DEBUG:
            print("<< set_value called")


    # I'm not sure that this function is ever used..
    def update(self, value): 
        """
        Update the current value, if necessary.

        value -- the value to update
        """
        if self.device.adapter.DEBUG:
            print("property -> update. Value = " + str(value))
        
        if value != self.value:
            if self.device.adapter.DEBUG:
                print("Value was different, updating.")
            self.value = value
            self.set_cached_value(value)
            self.device.notify_property_changed(self)
