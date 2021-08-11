# -*- coding: utf-8 -*-
from veusz.plugins import ToolsPlugin, toolspluginregistry

class SaveVSZSVGPlugin(ToolsPlugin):
    """Save as a re-editable SVG image with internal Veusz code."""
    menu = ('Save as Veusz-SVG',)
    name = 'Save as Veusz-SVG'
    description_short = 'Save as Veusz-SVG image.'
    description_full = 'Save as re-editable Veusz-SVG image.'

    def __init__(self):
        """Make list of fields."""
        from veusz.plugins import FieldInt
        self.fields = [ 
            FieldInt("pagenumber", default=1, descr="Page number of shown image"),
            ]

    def apply(self, interface, fields):
        """
        pagenum: The pagenumber of Veusz document to be exported as SVG image
        The script data will be saved in <metadata> element in the SVG file
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

        # Export normal SVG image
        namespace = r'{https://veusz.github.io/}'
        getSaveFileName = qt.QFileDialog.getSaveFileName
        (filepath, fltr) = getSaveFileName(caption='Save', filter="Images (*.svg)")
        if filepath[-4:] != ".svg":
            filepath += ".svg" 
        interface.Export(filepath, page=pagenum)

        # Add metadata to the exported SVG image
        tree = ET.parse(filepath)
        root = tree.getroot()
        metadata = ET.SubElement(root, 'metadata')
        veuszdata = ET.SubElement(metadata, f'{namespace}veusz')
        veuszdata.set("script", selfscript)
        tree.write(filepath, encoding="UTF-8")

toolspluginregistry.append(SaveVSZSVGPlugin)