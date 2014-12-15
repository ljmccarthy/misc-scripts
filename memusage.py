"""
MemoryUsageDialog is a simple tool for debugging memory leaks in wxPython
applications. It displays a list of all object types on the heap, the number of
objects and the total size taken up by all objects of that type (note: since
most Python objects store their data in a separate instance dict, this may be
misleading).

The text box at the top can be used to search for a particular type. The list
view is filtered on the text entered.

When a type is double-clicked, a tree view displays a list of up to 1000
instances of that type. Expanding items in the tree displays all objects that
reference the parent object.

The 'Collect' button tells Python to perform a full garbage collection and then
refreshes the display.

The 'Garbage' button displays a list of objects Python is unable to garbage
collect. This is usually due to the cyclical references containing objects that
implement the __del__() method.

To include MemoryUsageDialog in your application, simply import the class and
create it as you would any other wx.Dialog instance, e.g.

    from memusage import MemoryUsageDialog
    ...
    memdlg = MemoryUsageDialog(parent)
    memdlg.ShowModal()
    memdlg.Destroy()

Luke McCarthy, December 2014
"""

import sys
import gc
import re
import wx
from collections import defaultdict
from contextlib import contextmanager

def format_size(n):
    if n < 1024:
        return '%d B' % n
    elif n < 1024**2:
        return '%.2f KiB' % (float(n) / 1024)
    elif n < 1024**3:
        return '%.2f MiB' % (float(n) / 1024**2)
    else:
        return '%.2f GiB' % (float(n) / 1024**3)

def format_class(cls):
    return '%s.%s' % (cls.__module__, cls.__name__)

@contextmanager
def frozen_window(window):
    window.Freeze()
    try:
        yield window
    finally:
        try:
            window.Thaw()
        except Exception:
            pass

class HeapNode(object):
    __slots__ = ('obj', 'expanded')

    def __init__(self, obj):
        self.obj = obj
        self.expanded = False

class HeapReferrersFrame(wx.Frame):
    def __init__(self, root_title, roots):
        wx.Frame.__init__(self, None, size=(1200, 800), title='Heap Referrers - ' + root_title)
        self.tree = wx.TreeCtrl(self)
        self.tree.SetDoubleBuffered(True)
        root_item = self.tree.AddRoot(root_title)
        for root in roots:
            item = self.tree.AppendItem(root_item, repr(root))
            self.tree.SetPyData(item, HeapNode(root))
            self.tree.SetItemHasChildren(item, True)
            self.tree.Bind(wx.EVT_TREE_ITEM_EXPANDING, self.OnTreeItemExpanding)
        self.tree.Expand(root_item)
        self.Show()

    def OnTreeItemExpanding(self, evt):
        parent_item = evt.GetItem()
        node = self.tree.GetPyData(parent_item)
        if node and not node.expanded:
            referrers = [referrer for referrer in gc.get_referrers(node.obj) if not isinstance(referrer, HeapNode)]
            if referrers:
                for referrer in referrers:
                    item = self.tree.AppendItem(parent_item, repr(referrer))
                    self.tree.SetPyData(item, HeapNode(referrer))
                    self.tree.SetItemHasChildren(item, True)
                node.expanded = True
            else:
                evt.Veto()

class MemoryUsageDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, title='Python Memory Usage', size=wx.Size(500, 600), style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        self.sort_col = 0
        self.sort_rev = False

        self.filter = wx.TextCtrl(self)
        self.filter.SetFocus()

        self.listctrl = wx.ListCtrl(self, style=wx.LC_REPORT)
        self.listctrl.InsertColumn(0, 'Class', width=250)
        self.listctrl.InsertColumn(1, 'Size', width=100)
        self.listctrl.InsertColumn(2, 'Count', width=100)

        self.total_label = wx.StaticText(self, label='')
        btn_collect = wx.Button(self, label='&Collect')
        btn_garbage = wx.Button(self, label='&Garbage')
        btn_refresh = wx.Button(self, wx.ID_REFRESH)

        btnsizer = wx.BoxSizer(wx.HORIZONTAL)
        btnsizer.Add(self.total_label, 1, wx.ALIGN_CENTRE_VERTICAL)
        btnsizer.AddStretchSpacer()
        btnsizer.Add(btn_collect, 0, wx.ALIGN_CENTRE_VERTICAL)
        btnsizer.AddSpacer(5)
        btnsizer.Add(btn_garbage, 0, wx.ALIGN_CENTRE_VERTICAL)
        btnsizer.AddSpacer(5)
        btnsizer.Add(btn_refresh, 0, wx.ALIGN_CENTRE_VERTICAL)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.filter, 0, wx.EXPAND)
        sizer.Add(self.listctrl, 1, wx.EXPAND)
        sizer.Add(btnsizer, 0, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(sizer)

        self.Bind(wx.EVT_BUTTON, self.OnCollect, btn_collect)
        self.Bind(wx.EVT_BUTTON, self.OnGarbage, btn_garbage)
        self.Bind(wx.EVT_BUTTON, self.OnRefresh, btn_refresh)
        self.Bind(wx.EVT_TEXT, self.OnFilterChanged, self.filter)
        self.Bind(wx.EVT_LIST_COL_CLICK, self.OnColumnClicked)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemDClick)

        self.Refresh()

    def sort_ordering(self, item):
        x = item[self.sort_col]
        if self.sort_col == 0:
            return format_class(x)
        return x

    def SortData(self, col):
        if col == self.sort_col:
            self.sort_rev = not self.sort_rev
        else:
            self.sort_col = col
            self.sort_rev = col > 0
        self.data.sort(key=self.sort_ordering, reverse=self.sort_rev)

    def RefreshData(self):
        size_stats = defaultdict(int)
        count_stats = defaultdict(int)
        for obj in gc.get_objects():
            size_stats[type(obj)] += sys.getsizeof(obj)
            count_stats[type(obj)] += 1
        self.data = [(cls, size, count_stats[cls]) for (cls, size) in size_stats.iteritems()]
        self.data.sort(key=self.sort_ordering, reverse=self.sort_rev)

    def RepopulateList(self):
        pattern = re.compile(re.escape(self.filter.Value.strip()), re.I)
        with frozen_window(self.listctrl):
            self.listctrl.DeleteAllItems()
            for id, (cls, size, count) in enumerate(self.data):
                clsname = format_class(cls)
                if pattern.search(clsname):
                    index = self.listctrl.InsertStringItem(id, clsname)
                    self.listctrl.SetStringItem(index, 1, format_size(size))
                    self.listctrl.SetStringItem(index, 2, str(count))

    def GetSelectedClassName(self):
        selected_index = self.listctrl.GetNextItem(-1, wx.LIST_NEXT_ALL, wx.LIST_STATE_SELECTED)
        return self.listctrl.GetItemText(selected_index) if selected_index != wx.NOT_FOUND else ''

    def SetSelectedClassName(self, clsname):
        i = self.listctrl.FindItem(0, clsname)
        if i != wx.NOT_FOUND:
            self.listctrl.SetFocus()
            self.listctrl.EnsureVisible(i)
            self.listctrl.Select(i)

    def Refresh(self):
        with frozen_window(self.listctrl):
            clsname = self.GetSelectedClassName()
            self.RefreshData()
            self.RepopulateList()
            if clsname:
                self.SetSelectedClassName(clsname)

        total_size = sum(x[1] for x in self.data)
        total_count = sum(x[2] for x in self.data)
        self.total_label.SetLabel('Total: %d (%s)' % (total_count, format_size(total_size)))

    def OnRefresh(self, evt):
        self.Refresh()

    def OnCollect(self, evt):
        gc.collect()
        self.Refresh()

    def OnGarbage(self, evt):
        HeapReferrersFrame('Uncollectable Garbage', gc.garbage)

    def OnFilterChanged(self, evt):
        self.RepopulateList()

    def OnColumnClicked(self, evt):
        self.SortData(evt.GetColumn())
        self.RepopulateList()

    def find_class(self, clsname):
        for (cls, size, count) in self.data:
            if format_class(cls) == clsname:
                return cls

    def OnItemDClick(self, evt):
        cls = self.find_class(evt.GetItem().GetText())
        if cls:
            objs = []
            for obj in gc.get_objects():
                if type(obj) is cls:
                    objs.append(obj)
                if len(objs) >= 1000:
                    break
            title = 'Instances of {0.__module__}.{0.__name__}'.format(cls)
            HeapReferrersFrame(title, objs)

if __name__ == '__main__':
    app = wx.App()
    dlg = MemoryUsageDialog(None)
    dlg.ShowModal()
