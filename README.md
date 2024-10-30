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

It is possible to filter by object and/or interface name, thus only those services
that have an specific object or interface will be shown. If the `verbose` option
is not set, only the matching objects and/or interfaces for those services will
be shown, but if it is set, all the interfaces and objects in those services
will be shown. It is possible to use `wildcards` (both * and ?) for generic
searches.

It is also possible to filter by the service name (again, supporting wildcards),
to list only those services whose name matches the specified string.

Finally, it is possible to filter by process name (also with wildcard support),
thus showing only those services whose command line matches the specified string.

By default, only the well-known service names will be shown; using the `all`
parameter, instead, all the service names will be shown.
