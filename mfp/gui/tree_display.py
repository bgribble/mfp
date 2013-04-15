#! /usr/bin/env python
'''
tree_display.py
Wrapper around GtkTreeView and associated objects for the layer
and object lists

Copyright (c) 2013 Bill Gribble <grib@billgribble.com>
'''

from gi.repository import Gtk, GObject

class TreeDisplay (object): 
    def __init__(self, treeview, multisel, *columns):
        self.treeview = treeview 
        self.treestore = Gtk.TreeStore(GObject.TYPE_PYOBJECT)
        self.selection = self.treeview.get_selection()
        self.selected = []
        self.select_cb = None 
        self.unselect_cb = None 
        self.glib_select_cb_id = None

        self.object_paths = {} 
        self.object_parents = {} 
        self.columns = {} 
        self.columns_bynumber = {}

        if multisel:
            self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)

        self.treeview.set_model(self.treestore)
        self.glib_select_cb_id = self.selection.connect("changed", self._select_cb)

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
        getter = self.columns_bynumber[column][1]
        return getter(obj)

    def _obj_column_sorttext(self, obj, column):
        sorttext = self.columns_bynumber[column][4]
        default = self.columns_bynumber[column][1]
        if callable(sorttext):
            return sorttext(obj)
        else:
            return default(obj) 


    def _edited_cb(self, renderer, path, new_value):
        iter = self.treestore.get_iter_from_string(path)
        obj = self.treestore.get_value(iter, 0)
        colinfo = self.columns.get(renderer)
        colinfo[3](obj, new_value)
        return True

    def _select_cb(self, selection): 
        selections = [] 

        def selfn(mod, path, itr, data):
            selections[:0] = [self.treestore.get_value(itr, 0)]
        
        self.selection.selected_foreach(selfn, None)

        for s in self.selected:
            if s not in selections: 
                if self.unselect_cb:
                    self.unselect_cb(s)

        for s in selections: 
            if self.select_cb:
                self.select_cb(s)

        self.selected = selections

        return False 

    def _sort_func(self, model, iter_a, iter_b, data):
        obj_a = model.get_value(iter_a, 0)
        obj_b = model.get_value(iter_b, 0)

        return cmp(self._obj_column_sorttext(obj_a, 0), self._obj_column_sorttext(obj_b, 0))

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

    def unselect_all(self):
        to_remove = [s for s in self.selected ]
        for obj in to_remove:
            self.unselect(obj)

    def unselect(self, obj): 
        if obj not in self.selected: 
            return 
        else:
            self.selected.remove(obj)
            pathstr = self.object_paths.get(obj)
            if pathstr: 
                path = Gtk.TreePath.new_from_string(pathstr)
                self.selection.unselect_path(path)

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
        if obj in self.selected:
            need_select = True

        # temporarily disconnect signal handler  
        self.selection.disconnect(self.glib_select_cb_id)
        
        pathstr = self.object_paths.get(obj)
        path = Gtk.TreePath.new_from_string(pathstr)
        iter = self.treestore.get_iter_from_string(pathstr)

        # re-sort the object (and all its children, unfortunately)
        self.treestore.set(iter, 0, obj)

        # restore signal handler 
        self.glib_select_cb_id = self.selection.connect("changed", self._select_cb)
        self._update_paths()

        if need_select:
            pathstr = self.object_paths.get(obj)
            if pathstr: 
                path = Gtk.TreePath.new_from_string(pathstr)
                self.selection.select_path(path)

    def select(self, obj): 
        if obj in self.selected: 
            return 
        elif obj is None: 
            self.selected = [] 
            self.selection.unselect_all()
        else:
            self.selected[:0] = [obj] 
            pathstr = self.object_paths.get(obj)
            if pathstr: 
                path = Gtk.TreePath.new_from_string(pathstr)
                self.selection.select_path(path)





