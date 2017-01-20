from __future__ import print_function

from distutils.version import LooseVersion
import select
import sys
from threading import Thread
from time import sleep
import webbrowser

import wx

from .._wxutils import ID, Icon
from ..plot._base import backend
from .about import AboutFrame


APP = None  # hold the App instance
IS_OSX = sys.platform == 'darwin'
IS_WINDOWS = sys.platform.startswith('win')


def wildcard(filetypes):
    if filetypes:
        return '|'.join(map('|'.join, filetypes))
    else:
        return ""


class MenuBarMixin(object)
    """Mixin to create Eelbrain Menu

    On macOS, this has to be done on the Application level, otherwise on the
    frame level.

    """
    def __init__(self):
        self.menu_bar = menu_bar = wx.MenuBar()

        # File Menu
        m = wx.Menu()
        m.Append(wx.ID_OPEN, '&Open... \tCtrl+O')
        m.AppendSeparator()
        m.Append(wx.ID_CLOSE, '&Close Window \tCtrl+W')
        m.Append(wx.ID_SAVE, "Save \tCtrl+S")
        m.Append(wx.ID_SAVEAS, "Save As... \tCtrl+Shift+S")
        menu_bar.Append(m, "File")

        # Edit Menu
        m = wx.Menu()
        m.Append(ID.UNDO, '&Undo \tCtrl+Z')
        m.Append(ID.REDO, '&Redo \tCtrl+Shift+Z')
        m.AppendSeparator()
        m.Append(wx.ID_CUT, 'Cut \tCtrl+X')
        m.Append(wx.ID_COPY, 'Copy \tCtrl+C')
        m.Append(wx.ID_PASTE, 'Paste \tCtrl+V')
        m.AppendSeparator()
        m.Append(wx.ID_CLEAR, 'Cle&ar')
        menu_bar.Append(m, "Edit")

        # Tools Menu
        # updated by the active GUI
        m = wx.Menu()
        menu_bar.Append(m, "Tools")

        # View Menu
        m = wx.Menu()
        m.Append(ID.SET_VLIM, "Set Y-Axis Limit... \tCtrl+l", "Change the Y-"
                                                              "axis limit in epoch plots")
        m.Append(ID.SET_MARKED_CHANNELS, "Mark Channels...", "Mark specific "
                                                             "channels in plots.")
        m.AppendSeparator()
        m.Append(ID.SET_LAYOUT, "&Set Layout... \tCtrl+Shift+l", "Change the "
                                                                 "page layout")
        menu_bar.Append(m, "View")

        # Go Menu
        m = wx.Menu()
        m.Append(wx.ID_FORWARD, '&Forward \tCtrl+]', 'Go One Page Forward')
        m.Append(wx.ID_BACKWARD, '&Back \tCtrl+[', 'Go One Page Back')
        m.AppendSeparator()
        m.Append(ID.YIELD_TO_TERMINAL, '&Yield to Terminal \tAlt+Ctrl+Q')
        menu_bar.Append(m, "Go")

        # Window Menu
        m = wx.Menu()
        m.Append(ID.WINDOW_MINIMIZE, '&Minimize \tCtrl+M')
        m.Append(ID.WINDOW_ZOOM, '&Zoom')
        m.AppendSeparator()
        m.Append(ID.WINDOW_TILE, '&Tile')
        if IS_OSX:
            m.AppendSeparator()
        menu_bar.Append(m, "Window")

        # Help Menu
        m = wx.Menu()
        m.Append(ID.HELP_EELBRAIN, 'Eelbrain Help')
        m.Append(ID.HELP_PYTHON, "Python Help")
        m.AppendSeparator()
        m.Append(wx.ID_ABOUT, '&About Eelbrain')
        menu_bar.Append(m, self.GetMacHelpMenuTitleName() if IS_OSX else 'Help')

        # Bind Menu Commands
        self.Bind(wx.EVT_MENU_OPEN, self.OnMenuOpened)
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)
        self.Bind(wx.EVT_MENU, self.OnOpen, id=wx.ID_OPEN)
        self.Bind(wx.EVT_MENU, self.OnClear, id=wx.ID_CLEAR)
        self.Bind(wx.EVT_MENU, self.OnCloseWindow, id=wx.ID_CLOSE)
        self.Bind(wx.EVT_MENU, self.OnCopy, id=wx.ID_COPY)
        self.Bind(wx.EVT_MENU, self.OnCut, id=wx.ID_CUT)
        self.Bind(wx.EVT_MENU, self.OnOnlineHelp, id=ID.HELP_EELBRAIN)
        self.Bind(wx.EVT_MENU, self.OnOnlineHelp, id=ID.HELP_PYTHON)
        self.Bind(wx.EVT_MENU, self.OnPaste, id=wx.ID_PASTE)
        self.Bind(wx.EVT_MENU, self.OnRedo, id=ID.REDO)
        self.Bind(wx.EVT_MENU, self.OnSave, id=wx.ID_SAVE)
        self.Bind(wx.EVT_MENU, self.OnSaveAs, id=wx.ID_SAVEAS)
        self.Bind(wx.EVT_MENU, self.OnSetLayout, id=ID.SET_LAYOUT)
        self.Bind(wx.EVT_MENU, self.OnSetMarkedChannels, id=ID.SET_MARKED_CHANNELS)
        self.Bind(wx.EVT_MENU, self.OnSetVLim, id=ID.SET_VLIM)
        self.Bind(wx.EVT_MENU, self.OnUndo, id=ID.UNDO)
        self.Bind(wx.EVT_MENU, self.OnWindowMinimize, id=ID.WINDOW_MINIMIZE)
        self.Bind(wx.EVT_MENU, self.OnWindowTile, id=ID.WINDOW_TILE)
        self.Bind(wx.EVT_MENU, self.OnWindowZoom, id=ID.WINDOW_ZOOM)
        self.Bind(wx.EVT_MENU, self.OnQuit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.OnYieldToTerminal, id=ID.YIELD_TO_TERMINAL)

        # bind update UI
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUIBackward, id=wx.ID_BACKWARD)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUIClear, id=wx.ID_CLEAR)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUIClose, id=wx.ID_CLOSE)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUICopy, id=wx.ID_COPY)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUICut, id=wx.ID_CUT)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUIDown, id=wx.ID_DOWN)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUIForward, id=wx.ID_FORWARD)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUIOpen, id=wx.ID_OPEN)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUIPaste, id=wx.ID_PASTE)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUIRedo, id=ID.REDO)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUISave, id=wx.ID_SAVE)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUISaveAs, id=wx.ID_SAVEAS)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUISetLayout, id=ID.SET_LAYOUT)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUISetMarkedChannels, id=ID.SET_MARKED_CHANNELS)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUISetVLim, id=ID.SET_VLIM)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUITools, id=ID.TOOLS)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUIUndo, id=ID.UNDO)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUIUp, id=wx.ID_UP)


class MacApp(MenuBarMixin, App):
    def OnInit(self):
        MenuBarMixin.__init__(self)
        wx.MenuBar.MacSetCommonMenuBar(self.menubar)
        self.window_menu_window_items = []
        App.OnInit(self)


class App(wx.App):
    def OnInit(self):
        self.SetAppName("Eelbrain")
        self.SetAppDisplayName("Eelbrain")

        # Dock icon
        self.dock_icon = DockIcon(self)

        # register in IPython
        self.using_prompt_toolkit = False
        if ('IPython' in sys.modules and
                LooseVersion(sys.modules['IPython'].__version__) >=
                LooseVersion('5') and backend['prompt_toolkit']):
            import IPython

            IPython.terminal.pt_inputhooks.register('eelbrain',
                                                    self.pt_inputhook)
            shell = IPython.get_ipython()
            if shell is not None:
                shell.enable_gui('eelbrain')
                self.using_prompt_toolkit = True

                # qt4 backend can cause conflicts in IPython
                from .. import plot
                plot.configure(ets_toolkit='wx')
        self.SetExitOnFrameDelete(not self.using_prompt_toolkit)

        return True

    def pt_inputhook(self, context):
        """prompt_toolkit inputhook"""
        # prompt_toolkit.eventloop.inputhook.InputHookContext
        if IS_WINDOWS:
            # On Windows, select.poll() is not available
            def thread():
                while not context.input_is_ready():
                    sleep(.02)
                wx.CallAfter(self.pt_yield)
        else:
            def thread():
                poll = select.poll()
                poll.register(context.fileno(), select.POLLIN)
                poll.poll(-1)
                wx.CallAfter(self.pt_yield)

        Thread(target=thread).start()
        self.MainLoop()

    def pt_yield(self):
        self.ExitMainLoop(True)

    def _get_active_frame(self):
        win = wx.Window.FindFocus()
        win_parent = wx.GetTopLevelParent(win)
        if win_parent:
            return win_parent
        for w in wx.GetTopLevelWindows():
            if hasattr(w, 'IsActive') and w.IsActive():
                return w
        return wx.GetActiveWindow()

    def _get_parent_gui(self):
        frame = self._get_active_frame()
        if frame is None:
            return
        while True:
            if hasattr(frame, 'MakeToolsMenu'):
                return frame
            elif frame.Parent is not None:
                frame = frame.Parent
            else:
                return

    def _bash_ui(self, func, *args):
        "Launch a modal dialog based on terminal input"
        if self.IsMainLoopRunning():
            return func(False, *args)
        else:
            if not self.GetTopWindow():
                self.SetTopWindow(wx.Frame(None))
            wx.CallLater(10, func, True, *args)
            print("Please switch to the Python Application to provide input.")
            self.MainLoop()
            return self._result

    def ask_for_dir(self, title="Select Folder", message="Please Pick a Folder",
                    must_exist=True):
        return self._bash_ui(self._ask_for_dir, title, message, must_exist)

    def _ask_for_dir(self, exit_main_loop, title, message, must_exist):
        style = wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        if must_exist:
            style = style | wx.DD_DIR_MUST_EXIST

        dialog = wx.DirDialog(None, message, name=title,
                              style=style)
        dialog.SetTitle(title)
        if dialog.ShowModal() == wx.ID_OK:
            result = dialog.GetPath()
        else:
            result = False

        if exit_main_loop:
            self._result = result
            self.ExitMainLoop()
        else:
            return result

    def ask_for_file(self, title, message, filetypes, directory, mult):
        return self._bash_ui(self._ask_for_file, title, message, filetypes,
                             directory, mult)

    def _ask_for_file(self, exit_main_loop, title, message, filetypes,
                      directory, mult):
        """Returns path(s) or False.

        Parameters
        ----------
        ...
        directory : str
            Path to initial directory.

        Returns
        -------
        Result : list | str | None
            Paths(s) or False.
        """
        style = wx.FD_OPEN
        if mult:
            style = style | wx.FD_MULTIPLE
        dialog = wx.FileDialog(None, message, directory,
                               wildcard=wildcard(filetypes), style=style)
        dialog.SetTitle(title)
        if dialog.ShowModal() == wx.ID_OK:
            if mult:
                result = dialog.GetPaths()
            else:
                result = dialog.GetPath()
        else:
            result = False

        if exit_main_loop:
            self._result = result
            self.ExitMainLoop()
        else:
            return result

    def ask_for_string(self, title, message, default=''):
        return self._bash_ui(self._ask_for_string, title, message, default)

    def _ask_for_string(self, exit_main_loop, title, message, default):
        dlg = wx.TextEntryDialog(None, message, title, default)
        if dlg.ShowModal() == wx.ID_OK:
            result = dlg.GetValue()
        else:
            result = False

        if exit_main_loop:
            self._result = result
            self.ExitMainLoop()
        else:
            return result

    def ask_saveas(self, title, message, filetypes, defaultDir, defaultFile):
        return self._bash_ui(self._ask_saveas, title, message, filetypes,
                             defaultDir, defaultFile)

    def _ask_saveas(self, exit_main_loop, title, message, filetypes, defaultDir,
                    defaultFile):
        # setup file-dialog
        dialog = wx.FileDialog(None, message, wildcard=wildcard(filetypes),
                               style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        dialog.SetTitle(title)
        if defaultDir:
            dialog.SetDirectory(defaultDir)
        if defaultFile:
            dialog.SetFilename(defaultFile)
        # get result
        if dialog.ShowModal() == wx.ID_OK:
            result = dialog.GetPath()
        else:
            result = False

        if exit_main_loop:
            self._result = result
            self.ExitMainLoop()
        else:
            return result

    def message_box(self, message, caption, style):
        return self._bash_ui(self._message_box, message, caption, style)

    def _message_box(self, exit_main_loop, message, caption, style):
        result = wx.MessageBox(message, caption, style)

        if exit_main_loop:
            self._result = result
            self.ExitMainLoop()
        else:
            return result

    def ExitMainLoop(self, event_with_pt=True):
        if event_with_pt or not self.using_prompt_toolkit:
            # with prompt-toolkit, this leads to hanging when terminating the
            # interpreter
            wx.App.ExitMainLoop(self)

    def OnAbout(self, event):
        if hasattr(self, '_about_frame') and hasattr(self._about_frame, 'Raise'):
            self._about_frame.Raise()
        else:
            self._about_frame = AboutFrame(None)
            self._about_frame.Show()

    def OnClear(self, event):
        frame = self._get_active_frame()
        frame.OnClear(event)

    def OnCloseWindow(self, event):
        frame = self._get_active_frame()
        if frame is not None:
            frame.Close()

    def OnCopy(self, event):
        win = wx.Window.FindFocus()
        win.Copy()
#
    def OnCut(self, event):
        win = wx.Window.FindFocus()
        win.Cut()

    def OnMenuOpened(self, event):
        "Updates window names in the window menu"
        menu = event.GetMenu()
        if menu.GetTitle() == 'Window':
            # clear old entries
            while self.window_menu_window_items:
                item = self.window_menu_window_items.pop()
                menu.RemoveItem(item)
                self.Unbind(wx.EVT_MENU, id=item.GetId())
            # add new entries
            for window in wx.GetTopLevelWindows():
                id_ = window.GetId()
                label = window.GetTitle()
                if not label:
                    continue
                item = menu.Append(id_, label)
                self.Bind(wx.EVT_MENU, self.OnWindowRaise, id=id_)
                self.window_menu_window_items.append(item)
        elif menu.GetTitle() == 'Tools':
            for item in menu.GetMenuItems():
                menu.RemoveItem(item)
            frame = self._get_parent_gui()
            if frame:
                frame.MakeToolsMenu(menu)

    def OnOnlineHelp(self, event):
        "Called from the Help menu to open external resources"
        Id = event.GetId()
        if Id == ID.HELP_EELBRAIN:
            webbrowser.open("https://pythonhosted.org/eelbrain/")
        elif Id == ID.HELP_PYTHON:
            webbrowser.open("http://docs.python.org/2.7/")
        else:
            raise RuntimeError("Invalid help ID")

    def OnOpen(self, event):
        frame = self._get_active_frame()
        frame.OnOpen(event)

    def OnPaste(self, event):
        win = wx.Window.FindFocus()
        win.Paste()

    def OnQuit(self, event):
        for win in wx.GetTopLevelWindows():
            if not win.Close():
                return
        self.ExitMainLoop()

    def OnRedo(self, event):
        frame = self._get_active_frame()
        frame.OnRedo(event)

    def OnSave(self, event):
        frame = self._get_active_frame()
        frame.OnSave(event)

    def OnSaveAs(self, event):
        frame = self._get_active_frame()
        frame.OnSaveAs(event)

    def OnSetVLim(self, event):
        frame = self._get_active_frame()
        frame.OnSetVLim(event)

    def OnSetLayout(self, event):
        frame = self._get_active_frame()
        frame.OnSetLayout(event)

    def OnSetMarkedChannels(self, event):
        frame = self._get_active_frame()
        frame.OnSetMarkedChannels(event)

    def OnUndo(self, event):
        frame = self._get_active_frame()
        frame.OnUndo(event)

    def OnUpdateUIBackward(self, event):
        frame = self._get_active_frame()
        if frame and hasattr(frame, 'OnUpdateUIBackward'):
            frame.OnUpdateUIBackward(event)
        else:
            event.Enable(False)

    def OnUpdateUIClear(self, event):
        frame = self._get_active_frame()
        if frame and hasattr(frame, 'OnUpdateUIClear'):
            frame.OnUpdateUIClear(event)
        else:
            event.Enable(False)

    def OnUpdateUIClose(self, event):
        frame = self._get_active_frame()
        if frame and hasattr(frame, 'OnUpdateUIClose'):
            frame.OnUpdateUIClose(event)
        else:
            event.Enable(False)

    def OnUpdateUICopy(self, event):
        win = wx.Window.FindFocus()
        event.Enable(win and hasattr(win, 'CanCopy') and win.CanCopy())

    def OnUpdateUICut(self, event):
        win = wx.Window.FindFocus()
        event.Enable(win and hasattr(win, 'CanCut') and win.CanCut())

    def OnUpdateUIDown(self, event):
        frame = self._get_active_frame()
        if frame and hasattr(frame, 'OnUpdateUIDown'):
            frame.OnUpdateUIDown(event)
        else:
            event.Enable(False)

    def OnUpdateUIForward(self, event):
        frame = self._get_active_frame()
        if frame and hasattr(frame, 'OnUpdateUIForward'):
            frame.OnUpdateUIForward(event)
        else:
            event.Enable(False)

    def OnUpdateUIOpen(self, event):
        frame = self._get_active_frame()
        if frame and hasattr(frame, 'OnUpdateUIOpen'):
            frame.OnUpdateUIOpen(event)
        else:
            event.Enable(False)

    def OnUpdateUIPaste(self, event):
        win = wx.Window.FindFocus()
        event.Enable(win and hasattr(win, 'CanPaste') and win.CanPaste())

    def OnUpdateUIRedo(self, event):
        frame = self._get_active_frame()
        if frame and hasattr(frame, 'OnUpdateUIRedo'):
            frame.OnUpdateUIRedo(event)
        else:
            event.Enable(False)

    def OnUpdateUISave(self, event):
        frame = self._get_active_frame()
        if frame and hasattr(frame, 'OnUpdateUISave'):
            frame.OnUpdateUISave(event)
        else:
            event.Enable(False)

    def OnUpdateUISaveAs(self, event):
        frame = self._get_active_frame()
        if frame and hasattr(frame, 'OnUpdateUISaveAs'):
            frame.OnUpdateUISaveAs(event)
        else:
            event.Enable(False)

    def OnUpdateUISetLayout(self, event):
        frame = self._get_active_frame()
        if frame and hasattr(frame, 'OnUpdateUISetLayout'):
            frame.OnUpdateUISetLayout(event)
        else:
            event.Enable(False)

    def OnUpdateUISetMarkedChannels(self, event):
        frame = self._get_active_frame()
        if frame and hasattr(frame, 'OnUpdateUISetMarkedChannels'):
            frame.OnUpdateUISetMarkedChannels(event)
        else:
            event.Enable(False)

    def OnUpdateUISetVLim(self, event):
        frame = self._get_active_frame()
        if frame and hasattr(frame, 'OnUpdateUISetVLim'):
            frame.OnUpdateUISetVLim(event)
        else:
            event.Enable(False)

    def OnUpdateUITools(self, event):
        event.Enable(bool(self._get_parent_gui))

    def OnUpdateUIUndo(self, event):
        frame = self._get_active_frame()
        if frame and hasattr(frame, 'OnUpdateUIUndo'):
            frame.OnUpdateUIUndo(event)
        else:
            event.Enable(False)

    def OnUpdateUIUp(self, event):
        frame = self._get_active_frame()
        if frame and hasattr(frame, 'OnUpdateUIUp'):
            frame.OnUpdateUIUp(event)
        else:
            event.Enable(False)

    def OnWindowMinimize(self, event):
        frame = self._get_active_frame()
        if frame:
            frame.Iconize()

    def OnWindowRaise(self, event):
        id_ = event.GetId()
        window = wx.FindWindowById(id_)
        window.Raise()

    def OnWindowTile(self, event):
        frames = sorted(wx.GetTopLevelWindows(), lambda x, y: x.Position[0] < y.Position[0])
        dx, dy = wx.DisplaySize()
        x = 0
        y = 0
        y_next = 0
        for frame in frames:
            sx, sy = frame.Size
            if x and x + sx > dx:
                if y_next > dy:
                    return
                x = 0
                y = y_next
            frame.Position = (x, y)
            y_next = max(y_next, y + sy)
            x += sx

    def OnWindowZoom(self, event):
        frame = self._get_active_frame()
        if frame:
            frame.Maximize()

    def OnYieldToTerminal(self, event):
        self.ExitMainLoop()


def get_app():
    global APP
    if APP is None:
        APP = App()
    return APP


def run():
    app = get_app()
    if not app.using_prompt_toolkit and not app.IsMainLoopRunning():
        print("Starting GUI. Quit the Python application to return to the shell...")
        app.MainLoop()


class DockIcon(wx.TaskBarIcon):
    # http://stackoverflow.com/a/38249390/166700
    def __init__(self, app):
        wx.TaskBarIcon.__init__(self, iconType=wx.TBI_DOCK)
        self.app = app

        # Set the image
        self.SetIcon(Icon('eelbrain256', True), "Eelbrain")
        self.imgidx = 1

    def CreatePopupMenu(self):
        if not self.app.using_prompt_toolkit:
            menu = wx.Menu()
            menu.Append(ID.YIELD_TO_TERMINAL, '&Yield to Terminal')
            return menu
