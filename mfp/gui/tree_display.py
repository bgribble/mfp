#! /usr/bin/env python
'''
tree_display.py
Wrapper around GtkTreeView and associated objects for the layer
and object lists

Copyright (c) 2013 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Gtk, GObject

class TreeDisplay (object): 
    def __init__(self, treeview, *columns):
        self.treeview = treeview 
        self.treestore = Gtk.TreeStore(GObject.TYPE_PYOBJECT)
        self.selection = self.treeview.get_selection()
        self.selected_obj = None 
        self.select_cb = None 
        self.unselect_cb = None 

        self.object_paths = {} 
        self.object_parents = {} 
        self.columns = {} 
        self.columns_bynumber = {}

        self.treeview.set_model(self.treestore)
        self.selection.connect("changed", self._select_cb)

        colnum = 0
        for c in columns:
            title, thunk, editable, callback = c 
            r = Gtk.CellRendererText()
            r.set_property("editable", editable)
            if editable and callback:
                r.connect("edited", callback)
            col = Gtk.TreeViewColumn(title, r)
            col.set_cell_data_func(r, self.extract_col_cb) 
            self.columns[r] = c
            self.columns_bynumber[colnum] = c
            self.treeview.append_column(col)
            colnum += 1

        self.treestore.set_sort_column_id(0, Gtk.SortType.ASCENDING)
        self.treestore.set_sort_func(0, self._sort_func)
        self.treeview.expand_all()

    def _obj_column_text(self, obj, column):
        getter = self.columns_bynumber[0][1]
        return getter(obj)

    def _select_cb(self, selection): 
        model, iter = self.selection.get_selected()
        if iter is None and self.selected_obj is not None:
            self.unselect_cb(self.selected_obj)
        elif iter is not None:
            obj = self.treestore.get_value(iter, 0)
            if obj is not self.selected_obj:
                self.unselect_cb(self.selected_obj)
                self.selected_obj = obj 
                self.select_cb(obj)
        return False 

    def _sort_func(self, model, iter_a, iter_b, data):
        obj_a = model.get_value(iter_a, 0)
        obj_b = model.get_value(iter_b, 0)

        return cmp(self._obj_column_text(obj_a, 0), self._obj_column_text(obj_b, 0))


    def _update_paths(self):
        p = {} 
        def thunk(model, path, iter, data):
            obj = self.treestore.get_value(iter, 0)
            p[obj] = path.to_string() 
            return False 

        self.treestore.foreach(thunk, None)
        self.object_paths = p

    def extract_col_cb(self, treecol, renderer, model, iterator, data, *args):
        thunk = self.columns.get(renderer)[1]
        obj = self.treestore.get_value(iterator, 0)
        renderer.set_property("text", thunk(obj))

    def clear(self):
        self.treestore.clear()
        self.object_paths = {} 

    def insert(self, obj, parent):
        from .patch_layer import PatchLayer 
        piter = None 
        if parent is not None:
            ppath = self.object_paths.get(parent)
            if ppath is not None:
                piter = self.treestore.get_iter_from_string(ppath)

        iter = self.treestore.append(piter)
        self.treestore.set_value(iter, 0, obj)
        self.object_parents[obj] = parent 
        self._update_paths() 
        self.treeview.expand_all()

    def remove(self, obj):
        path = self.object_paths.get(obj)
        if path: 
            iter = self.treestore.get_iter_from_string(path)
        self.treestore.remove(iter)
        self._update_paths()

    def update(self, obj, parent):
        pathstr = self.object_paths.get(obj)
        path = Gtk.TreePath.new_from_string(pathstr)
        iter = self.treestore.get_iter_from_string(pathstr)
        self.treestore.remove(iter)
        self.insert(obj, parent)

    def select(self, obj): 
        if self.selected_obj is obj: 
            return 
        elif obj is None: 
            self.selected_obj = None 
            self.selection.unselect_all()
        else:
            self.selected_obj = obj 
            pathstr = self.object_paths.get(obj)
            if pathstr: 
                path = Gtk.TreePath.new_from_string(pathstr)
                self.selection.select_path(path)





