#! /usr/bin/env python
'''
layer.py
A layer in the patch window
'''
from abc import ABC, abstractmethod
from .backend_interfaces import BackendInterface


class LayerImpl(ABC):
    @abstractmethod
    def show(self):
        pass

    @abstractmethod
    def hide(self):
        pass


class Layer(BackendInterface):
    backend_name = None

    def __init__(self, app_window, patch, name, scope="__patch__"):
        self.app_window = app_window
        self.patch = patch
        self.name = name
        self.scope = scope
        self.objects = []
        super().__init__()

    @classmethod
    def build(cls, *args, **kwargs):
        return cls.get_backend(cls.backend_name)(*args, **kwargs)

    def resort(self, obj):
        if obj in self.objects:
            self.objects.remove(obj)
        self.add(obj)

    def add(self, obj, container=None):
        BAD = 1000000
        obj.layer = self
        obj.layername = self.name

        def distance(left, right):
            d1 = ((obj.position_x - left.position_x) ** 2
                  + (obj.position_y - left.position_y) ** 2) ** 0.5
            d2 = ((obj.position_x - right.position_x) ** 2
                  + (obj.position_y - right.position_y) ** 2) ** 0.5
            return d1 + d2

        if not len(self.objects):
            self.objects = [obj]
        elif ((obj.position_x < self.objects[0].position_x)
              and (obj.position_y < self.objects[0].position_y)):
            self.objects[:0] = [obj]
        elif ((obj.position_x > self.objects[-1].position_x)
              and (obj.position_y > self.objects[-1].position_y)):
            self.objects.append(obj)
        else:
            distances = []
            for i in range(len(self.objects) - 1):
                distances.append(distance(self.objects[i], self.objects[i + 1]))

            if ((obj.position_x < self.objects[0].position_x)
                    or (obj.position_y < self.objects[0].position_y)):
                distances[0:0] = [distance(self.objects[0], self.objects[0])]
            else:
                distances[0:0] = [BAD]

            if ((obj.position_x > self.objects[-1].position_x)
                    or (obj.position_y > self.objects[-1].position_y)):
                distances.append(distance(self.objects[-1], self.objects[-1]))
            else:
                distances.append(BAD)

            newloc = distances.index(min(distances))
            self.objects[newloc:newloc] = [obj]

    def remove(self, obj):
        if obj in self.objects:
            self.objects.remove(obj)
        obj.layer = None
