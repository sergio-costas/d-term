# D-TERM

This is a DBus tool that allows to get info about the current DBus services,
their objects and interfaces. It is similar to D-FEET, but in text mode. That
makes it useful for those cases where a graphical environment isn't available.

## Using it

The basic call method is

    d-term --system

or
    d-term --session

to list all the services in the system or session bus, the corresponding process
running behind, their objects, and all the interfaces in each object.

It is possible to filter 
