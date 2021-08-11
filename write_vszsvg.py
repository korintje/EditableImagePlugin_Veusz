# -*- coding: utf-8 -*-
from veusz.plugins import ToolsPlugin, toolspluginregistry

class WriteVSZSVGPlugin(ToolsPlugin):
    """Write an editable SVG image which contains internal Veusz code."""
    menu = ('Write Editable SVG',)
    name = 'Write Editable SVG'
    description_short = 'Write an editable SVG image.'
    description_full = 'Write an editable SVG image containing Veusz code.'

    def __init__(self):
        """Make list of fields."""
        from veusz.plugins import FieldInt
        self.fields = [ 
            FieldInt("pagenumber", default=1, descr="Page number of shown image"),
            ]

    def apply(self, interface, fields):
        """Do the work of the plugin.
        interface: veusz command line interface object (exporting commands)
        fields: dict mapping field names to values
        """
        import xml.etree.ElementTree as ET
        import veusz.qtall as qt
        import os, tempfile

        # get the Node corresponding to the widget path given
        pagenum = fields['pagenumber'] - 1

        # Save temporary .vsz document
        tmpdir = tempfile.TemporaryDirectory()
        tmpvsz = os.path.join(tmpdir.name, 'tmp.vsz')
        try:
            interface.Save(tmpvsz)
            with open(tmpvsz, 'r') as f:
                selfscript = f.read()
        except:
            pass
        os.remove(tmpvsz)
        tmpdir.cleanup()

        # Export normal SVG
        namespace = r'{https://veusz.github.io/}'
        (filepath, selectedFilter) = qt.QFileDialog.getSaveFileName(caption = 'Save')

        interface.Export(filepath, page=pagenum)
        tree = ET.parse(filepath)
        root = tree.getroot()
        metadata = ET.SubElement(root, 'metadata')
        veuszdata = ET.SubElement(metadata, f'{namespace}veusz')
        veuszdata.set("script", selfscript)
        tree.write(filepath, encoding="UTF-8")

toolspluginregistry.append(WriteVSZSVGPlugin)