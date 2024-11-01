#!/usr/bin/env python3

import dbus
import sys
import xml.etree.ElementTree as ET
import time
import argparse
import fnmatch

parser = argparse.ArgumentParser(prog="dbus-txt", description="A command line utility to list dbus services in either the system or the session bus, and filter by object, interface or service name.")
group = parser.add_mutually_exclusive_group()
group.add_argument('--system', action='store_true', help="List services from the system bus")
group.add_argument('--session', action='store_true', help="List services from the session bus")
parser.add_argument('-o', '--object', help="Show only services that have an object that matches this (can use * and ? as wildcards)")
parser.add_argument('-i', '--interface', help="Show only services that have an interface that matches this (can use * and ? as wildcards)")
parser.add_argument('-s', '--service', help="Show only services whose name matches this (can use * and ? as wildcards)")
parser.add_argument('-p', '--process', help="Show only services whose cmd line matches this (can use * and ? as wildcards)")
parser.add_argument('-a', '--all', action='store_true', help="Show also private names (:X.Y)")
parser.add_argument('-w', '--wakeup', action='store_true', help="Show info for activatable services")
parser.add_argument('-v', '--verbose', action='store_true', help="Show all the service info when doing an object, interface or process filtering")
args = parser.parse_args()

if args.system:
    current_bus = dbus.SystemBus()
elif args.session:
    current_bus = dbus.SessionBus()
else:
    parser.print_help()
    sys.exit(1)

search_object = args.object
search_interface = args.interface
search_service = args.service
search_process = args.process
verbose = args.verbose
all = args.all
wakeup = args.wakeup

class dbus_service:
    counter = 0
    last_time = 0

    def __init__(self, bus, name, activated = True):
        self._bus = bus
        self._name = name
        self._executable = None
        self._activated = activated
        self._pid = None
        self._objects = {}
        if activated:
            self._objects = self._get_objects(bus, name)
            # try to get the executable
            self._find_executable()

    def _find_executable(self):
        proxy = self._bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
        try:
            self._pid = proxy.GetConnectionUnixProcessID(self._name, dbus_interface='org.freedesktop.DBus')
        except:
            return
        proc_file = f"/proc/{self._pid}/cmdline"
        with open(proc_file, "r") as proc_data:
            self._executable = proc_data.readline().replace("\0", " ").strip()

    def _get_objects(self, bus, name):
        obj = dbus_object(bus, name, '', None)
        object_list = obj.get_children_objects()
        return object_list

    def get_name(self):
        return self._name

    def get_objects(self):
        return self._objects

    def get_executable(self):
        return self._executable, self._pid

    def has_object(self, object_path):
        if object_path is None:
            return True
        return len(fnmatch.filter(self._objects, object_path)) != 0

    def has_interface(self, interface_name):
        if interface_name is None:
            return True
        for object in self._objects:
            if object.has_interface(interface_name):
                return True
        return False

    @staticmethod
    def show_progress():
        if time.time()-dbus_service.last_time < .1:
            return
        dbus_service.last_time = time.time()
        if dbus_service.counter == 0:
            print('/', file=sys.stderr, end='\r')
            dbus_service.counter = 1
        elif dbus_service.counter == 1:
            print('-', file=sys.stderr, end='\r')
            dbus_service.counter = 2
        elif dbus_service.counter == 2:
            print('\\', file=sys.stderr, end='\r')
            dbus_service.counter = 3
        else:
            print('|', file=sys.stderr, end='\r')
            dbus_service.counter = 0


    @staticmethod
    def dbus_array_to_python(darray):
        return [element for element in darray]

    @staticmethod
    def get_services(bus, find_all, wake_up):
        proxy = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
        output = []
        names = dbus_service.dbus_array_to_python(proxy.ListNames(dbus_interface='org.freedesktop.DBus'))
        activatable_names = dbus_service.dbus_array_to_python(proxy.ListActivatableNames(dbus_interface='org.freedesktop.DBus'))

        for name in names:
            dbus_service.show_progress()
            if name[0] == ':' and not find_all:
                continue
            output.append(dbus_service(bus, name))

        for name in activatable_names:
            if name in names:
                continue
            print(f"Waking up service {name}")
            output.append(dbus_service(bus, name, wake_up))

        return output

class dbus_object:
    def __init__(self, bus, service_name, object_name, parent_object):
        self._bus = bus
        self._service_name = service_name
        self._object_name = object_name
        self._parent_object = parent_object
        self._child_objects = []
        self._interfaces = []
        self._get_introspection()

    def has_interface(self, interface_name):
        if interface_name is None:
            return True
        return len(fnmatch.filter(self._interfaces, interface_name)) != 0

    def get_interfaces(self):
        if self._interfaces is None:
            return []
        return self._interfaces

    def get_path(self):
        parent = self._parent_object.get_path() if self._parent_object is not None else ''
        if parent == '/':
            parent = ''
        return parent + '/' + self._object_name

    def _get_introspection(self):
        try:
            proxy = self._bus.get_object(self._service_name, self.get_path())
        except:
            self._interfaces = None
            print(f"Failed to connect to service {self._service_name}")
            return
        try:
            introspect_data = str(proxy.Introspect(dbus_interface='org.freedesktop.DBus.Introspectable'))
        except:
            self._interfaces = None
            return
        tree = ET.fromstring(introspect_data)
        for child in tree:
            dbus_service.show_progress()
            if child.tag == 'node' and 'name' in child.attrib:
                self._child_objects.append(dbus_object(self._bus, self._service_name, child.attrib['name'], self))
                continue
            if child.tag == 'interface' and 'name' in child.attrib:
                self._interfaces.append(child.attrib['name'])
                continue

    def get_children_objects(self):
        if self._interfaces is None or len(self._interfaces) != 0:
            children = {self.get_path(): self}
        else:
            children = {}
        for child in self._child_objects:
            children = children | child.get_children_objects()
        return children

def print_service_data(service, service_list):
    global verbose
    global search_interface
    global search_object
    global search_process

    if service.processed:
        return

    executable, pid = service.get_executable()
    # print all the services that share the same process
    for s in service_list:
        exec, pid2 = s.get_executable()
        if pid == pid2:
            print(s.get_name())
            s.processed = True
    if executable is None:
        executable = "Unknown"
        pid = "Not running"
    print(f"  Cmd line: {executable} (Pid: {pid})")
    if search_process is not None and not verbose:
        return
    objects = service.get_objects()
    for object_name in objects:
        if (not verbose) and (not objects[object_name].has_interface(search_interface)):
            continue
        if (not verbose) and (search_interface is None) and (search_object is not None) and (not fnmatch.fnmatch(object_name, search_object)):
            continue
        print(f"  {object_name}")
        for interface_name in objects[object_name].get_interfaces():
            print(f"    {interface_name}")
    print()

services = dbus_service.get_services(current_bus, all, wakeup)

if search_service is not None:
    services = [service for service in services if fnmatch.fnmatch(service.get_name(), search_service)]

def sort_services(e):
    if e.get_executable()[0] is None:
        return ""
    return e.get_name()

found = False
services.sort(key=sort_services)

for service in services:
    service.processed = False

for service in services:
    if not service.has_object(search_object) or not service.has_interface(search_interface):
        continue
    if (search_process is not None) and (not fnmatch.fnmatch(service.get_executable()[0], search_process)):
        continue
    found = True
    print_service_data(service, services)

if not found:
    print("No DBus services found with the specified filters")
