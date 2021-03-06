"""Embedd Mayavi in Eelbrain

for testing:

src = datasets.get_mne_sample(src='ico', sub=[0])['src']
brain = plot.brain.brain(src.source, mask=False,hemi='lh',views='lat')
"""
from itertools import izip
from logging import getLogger

from mayavi.core.ui.api import SceneEditor, MlabSceneModel
import numpy as np
from traits.api import HasTraits, Instance
from traitsui.api import View, Item, HGroup, VGroup
from tvtk.api import tvtk
from tvtk.pyface.toolkit import toolkit_object
import wx

from .._wxgui.app import get_app
from .._wxgui.frame import EelbrainFrame
from .._wxutils import ID, Icon


SCENE_NAME = 'scene_%i'
SURFACES = ('inflated', 'pial', 'smoothwm')

# undecorated scene
Scene = toolkit_object('scene:Scene')


class MayaviView(HasTraits):

    view = Instance(View)

    def __init__(self, width, height, n_rows, n_columns):
        HasTraits.__init__(self)

        n_scenes = n_rows * n_columns
        if n_scenes < 1:
            raise ValueError("n_rows=%r, n_columns=%r" % (n_rows, n_columns))

        self.scenes = tuple(MlabSceneModel() for _ in xrange(n_scenes))
        for i, scene in enumerate(self.scenes):
            self.add_trait(SCENE_NAME % i, scene)

        if n_rows == n_columns == 1:
            self.view = View(Item(SCENE_NAME % 0,
                                  editor=SceneEditor(scene_class=Scene),
                                  resizable=True, show_label=False),
                             width=width, height=height, resizable=True)
        else:
            rows = []
            for row in xrange(n_rows):
                columns = []
                for column in xrange(n_columns):
                    i = row * n_columns + column
                    item = Item(SCENE_NAME % i,
                                editor=SceneEditor(scene_class=Scene),
                                resizable=True, show_label=False)
                    columns.append(item)
                rows.append(HGroup(*columns))
            self.view = View(VGroup(*rows))

        self.figures = [scene.mayavi_scene for scene in self.scenes]


class BrainFrame(EelbrainFrame):

    def __init__(self, parent, brain, title, width, height, n_rows, n_columns,
                 surf, pos):
        EelbrainFrame.__init__(self, parent, wx.ID_ANY, "Brain: %s" % title,
                               wx.DefaultPosition if pos is None else pos)

        # toolbar
        tb = self.CreateToolBar(wx.TB_HORIZONTAL)
        tb.SetToolBitmapSize(size=(32, 32))
        tb.AddLabelTool(wx.ID_SAVE, "Save", Icon("tango/actions/document-save"))
        self.Bind(wx.EVT_TOOL, self.OnSaveAs, id=wx.ID_SAVE)
        self.Bind(wx.EVT_UPDATE_UI, self.OnUpdateUISave, id=wx.ID_SAVE)
        # color-bar
        tb.AddLabelTool(ID.PLOT_COLORBAR, "Plot Colorbar", Icon("plot/colorbar"))
        tb.Bind(wx.EVT_TOOL, self.OnPlotColorBar, id=ID.PLOT_COLORBAR)
        # surface
        self._surf_selector = wx.Choice(
            tb, choices=[name.capitalize() for name in SURFACES],
            name='Surface')
        if surf in SURFACES:
            self._surf_selector.SetSelection(SURFACES.index(surf))
        tb.AddControl(self._surf_selector, "Surface")
        self._surf_selector.Bind(
            wx.EVT_CHOICE, self.OnChoiceSurface, source=self._surf_selector)
        # view
        tb.AddLabelTool(ID.VIEW_LATERAL, "Lateral View", Icon('brain/lateral'))
        self.Bind(wx.EVT_TOOL, self.OnSetView, id=ID.VIEW_LATERAL)
        tb.AddLabelTool(ID.VIEW_MEDIAL, "Medial View", Icon('brain/medial'))
        self.Bind(wx.EVT_TOOL, self.OnSetView, id=ID.VIEW_MEDIAL)
        # attach
        tb.AddStretchableSpace()
        tb.AddLabelTool(ID.ATTACH, "Attach", Icon("actions/attach"))
        self.Bind(wx.EVT_TOOL, self.OnAttach, id=ID.ATTACH)
        tb.Realize()

        self.mayavi_view = MayaviView(width, height, n_rows, n_columns)
        self._n_rows = n_rows
        self._n_columns = n_columns
        # Use traits to create a panel, and use it as the content of this
        # wx frame.
        self.ui = self.mayavi_view.edit_traits(parent=self,
                                               view=self.mayavi_view.view,
                                               kind='subpanel')
        self.panel = self.ui.control
        # Hide the toolbar (the edit_traits command assigns scene_editor)
        for scene in self.mayavi_view.scenes:
            scene.interactor.interactor_style = tvtk.InteractorStyleTerrain()

        self.SetImageSize(width, height)

        self.figure = self.mayavi_view.figures
        self._brain = brain
        self.Bind(wx.EVT_CLOSE, self.OnClose)  # remove circular reference

        # replace key bindings
        self.panel.Unbind(wx.EVT_KEY_DOWN)
        for child in self.panel.Children[0].Children:
            panel = child.Children[0]
            panel.Unbind(wx.EVT_CHAR)
            panel.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)

    def CanCopy(self):
        return True

    def Copy(self):
        ss = self._brain.screenshot('rgba', True)
        ss = np.round(ss * 255).astype(np.uint8)
        h, w, _ = ss.shape
        image = wx.ImageFromDataWithAlpha(
            w, h, ss[:,:,:3].tostring(), ss[:,:,3].tostring())
        bitmap = image.ConvertToBitmap()
        data = wx.BitmapDataObject(bitmap)
        if not wx.TheClipboard.Open():
            getLogger('eelbrain').debug("Failed to open clipboard")
            return
        try:
            wx.TheClipboard.SetData(data)
        finally:
            wx.TheClipboard.Close()
            wx.TheClipboard.Flush()

    def OnAttach(self, event):
        get_app().Attach(self._brain, "Brain plot", 'brain', self)

    def OnChoiceSurface(self, event):
        self._brain._set_surf(SURFACES[event.GetSelection()])

    def OnClose(self, event):
        event.Skip()
        if self._brain is not None:
            self._brain._surfer_close()
            # remove circular references
            self._brain._frame = None
            self._brain = None

    def OnKeyDown(self, event):
        if self._brain is None:
            return  # plot is closed
        key = unichr(event.GetUnicodeKey())
        if key == '.':
            self._brain._nudge_time(1)
        elif key == ',':
            self._brain._nudge_time(-1)
        else:
            event.Skip()

    def OnPlotColorBar(self, event):
        if self._brain._has_data():
            self._brain.plot_colorbar()
        elif self._brain._has_annot() or self._brain._has_labels():
            self._brain.plot_legend()

    def OnSave(self, event):
        self.OnSaveAs(event)

    def OnSaveAs(self, event):
        default_file = '%s.png' % self.GetTitle().replace(': ', ' - ')
        dlg = wx.FileDialog(self, "If no file type is selected below, it is "
                                  "inferred from the extension.",
                            defaultFile=default_file,
                            wildcard="Any (*.*)|*.*|PNG (*.png)|*.png",
                            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            # no antialiasing (leads to loss of alpha channel)
            self._brain.save_image(dlg.GetPath(), 'rgba')
        dlg.Destroy()

    def OnSetView(self, event):
        if event.Id == ID.VIEW_LATERAL:
            views = ('lateral', 'medial')
        elif event.Id == ID.VIEW_MEDIAL:
            views = ('medial', 'lateral')
        else:
            return

        for row, view in izip(self._brain.brain_matrix, views):
            for b in row:
                b.show_view(view)

    def OnUpdateUISave(self, event):
        event.Enable(True)

    def OnUpdateUISaveAs(self, event):
        event.Enable(True)

    def SetImageSize(self, width, height):
        if self._n_columns == 1 and self._n_rows == 1:
            width += 2
            height += 2
        else:
            width += self._n_columns * 2 + 4
            height += self._n_rows * 2 + 4
        self.SetClientSize((width, height))
