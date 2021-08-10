# -*- coding: utf-8 -*-
# import veusz.plugins as plugins
from veusz.plugins import (
    ToolsPlugin,   
    toolspluginregistry,
    )

class EditableSVGPlugin(ToolsPlugin):
    """Read/Write an editable SVG image which contains internal Veusz code."""
    
    menu = ('Read/Write Editable SVG',)
    name = 'Read/Write Editable SVG'
    description_short = 'Read/Write an editable SVG image.'
    description_full = 'Read/Write an editable SVG image containing Veusz code.'

    def __init__(self):
        """Make list of fields."""
        from veusz.plugins import FieldWidget, FieldMarker, FieldFilename, Field
        import veusz.qtall as qt

        class FieldFilesave(Field):
            """Select a filename to be saved with a browse button."""

            # def __init__(self, name, descr=None, default=''):
            #     _FieldSetting.__init__(
            #         self, setting.Filename, name, descr=descr, default=default)

            def __init__(self, name, descr=None, default=''):
                Field.__init__(self, name, descr=descr, default=default)
                self.default = default
                self.setn = setting.Filename(name, default)
                    
            def makeControl(self, doc, currentwidget):
                l = qt.QLabel(self.descr)
                c = qt.QDialogButtonBox.Save
                return (l, c)

        # self.buttonBox.button().setText(_('Export'))
        self.fields = [ 
            FieldWidget("widget", descr="Start from widget", default="/"),
            FieldMarker("markersearch", descr="Search for marker"),
            FieldMarker("markerreplace", descr="Replace with marker"),
            FieldFilename("markerreplace", descr="Replace with marker"),
            FieldFilesave("filepath", descr="Path for file save")
            ]

    def apply(self, interface, fields):
        """Do the work of the plugin.
        interface: veusz command line interface object (exporting commands)
        fields: dict mapping field names to values
        """

        # get the Node corresponding to the widget path given
        fromwidget = interface.Root.fromPath(fields['widget'])
        search = fields['markersearch']
        replace = fields['markerreplace']

        # loop over every xy widget including and below fromwidget
        for node in fromwidget.WalkWidgets(widgettype='xy'):
            # if marker is value given, replace
            if node.marker.val == search:
                node.marker.val = replace

toolspluginregistry.append(EditableSVGPlugin)