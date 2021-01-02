import wx
from os import getcwd
from fireman import FiReMan, HEADER


class Mywin(wx.Frame):

   def __init__(self, parent, title):
        super(Mywin, self).__init__(parent, size=wx.Size(1900, 600) , title = title)

        panel = wx.Panel(self)
        box = wx.BoxSizer(wx.HORIZONTAL)

        self.list = wx.ListCtrl(panel, -1, style = wx.LC_REPORT)
        for i, name in enumerate(["index"]+HEADER):
            self.list.InsertColumn(i, name.upper(), width=10)
        self.list.EnableCheckBoxes(True)

        frm = FiReMan()
        frm.scan_folder(getcwd(), filename_regex_filter=r".+\.jpg")
        file_list = frm.df.sort_values(by=["folder", "filename"], ascending=False, inplace=False)

        for idx, row in file_list.iterrows():
            index = self.list.InsertItem(0, str(idx))
            for i, col in enumerate(row[:-1]):
                self.list.SetItem(index, i+1, str(col))

        for i in range(self.list.GetColumnCount()):
            self.list.SetColumnWidth(i, wx.LIST_AUTOSIZE)

        box.Add(self.list, 1, wx.ALL | wx.EXPAND)
        panel.SetSizer(box)
        panel.Fit()
        self.Centre()

        self.Show(True)

ex = wx.App()
Mywin(None, 'FiReMan Demo')
ex.MainLoop()

