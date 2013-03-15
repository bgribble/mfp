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
        self.select_cb_id = None
        self.unselect_cb = None 

        self.object_paths = {} 
        self.object_parents = {} 
        self.columns = {} 
        self.columns_bynumber = {}

        self.treeview.set_model(self.treestore)
        self.select_cb_id = self.selection.connect("changed", self._select_cb)

        colnum = 0
        for c in columns:
            title, thunk, editable, callback, sort = c 
            r = Gtk.CellRendererText()
            r.set_property("editable", editable)
            if editable and callback:
                r.connect("edited", self._edited_cb)
            col = Gtk.TreeViewColumn(title, r)
            col.set_cell_data_func(r, self.extract_col_cb) 
            self.columns[r] = c
            self.columns_bynumber[colnum] = c
            self.treeview.append_column(col)
            if sort: 
                self.treestore.set_sort_column_id(colnum, Gtk.SortType.ASCENDING)
                self.treestore.set_sort_func(colnum, self._sort_func)
            colnum += 1

        self.treeview.expand_all()

    def _obj_column_text(self, obj, column):
        getter = self.columns_bynumber[0][1]
        return getter(obj)

    def _edited_cb(self, renderer, path, new_value):
        iter = self.treestore.get_iter_from_string(path)
        obj = self.treestore.get_value(iter, 0)
        colinfo = self.columns.get(renderer)
        colinfo[3](obj, new_value)
        return True

    def _select_cb(self, selection): 
        model, iter = self.selection.get_selected()
        if iter is None and self.unselect_cb and self.selected_obj is not None:
            self.unselect_cb(self.selected_obj)
        elif iter is not None:
            obj = self.treestore.get_value(iter, 0)
            if obj is not self.selected_obj:
                if self.unselect_cb:
                    self.unselect_cb(self.selected_obj)
                self.selected_obj = obj 
                if self.select_cb:
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

    def unselect(self, obj): 
        print "TreeDisplay.unselect not done yet"

    def insert(self, obj, parent):
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
        return iter 

    def move_before(self, obj, target):
        path = self.object_paths.get(obj)
        iter_old = self.treestore.get_iter_from_string(path) 
        path = self.object_paths.get(target)
        iter_new = self.treestore.get_iter_from_string(path) 
        self.treestore.move_before(iter_old, iter_new)
        self._update_paths()

    def move_after(self, obj, target):
        path = self.object_paths.get(obj)
        iter_old = self.treestore.get_iter_from_string(path) 
        path = self.object_paths.get(target)
        iter_new = self.treestore.get_iter_from_string(path) 
        self.treestore.move_after(iter_old, iter_new)
        self._update_paths()

    def remove(self, obj):
        path = self.object_paths.get(obj)
        if path: 
            iter = self.treestore.get_iter_from_string(path)
            self.treestore.remove(iter)
            self._update_paths()

    def update(self, obj, parent):
        need_select = False 
        if self.selected_obj == obj:
            need_select = True

        pathstr = self.object_paths.get(obj)
        path = Gtk.TreePath.new_from_string(pathstr)
        iter = self.treestore.get_iter_from_string(pathstr)

        # temporarily disconnect signal handler  
        self.selection.disconnect(self.select_cb_id)
        self.treestore.remove(iter)
        self.insert(obj, parent)

        # restore signal handler 
        self.select_cb_id = self.selection.connect("changed", self._select_cb)
        self._update_paths()

        if need_select:
            pathstr = self.object_paths.get(obj)
            if pathstr: 
                path = Gtk.TreePath.new_from_string(pathstr)
                self.selection.select_path(path)


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





