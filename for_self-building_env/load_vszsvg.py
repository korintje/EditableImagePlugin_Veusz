# -*- coding: utf-8 -*-
from veusz.plugins import ToolsPlugin, toolspluginregistry

class LoadVSZSVGPlugin(ToolsPlugin):
    """Load a re-editable SVG image with internal Veusz code."""
    menu = ('Load Veusz-SVG',)
    name = 'Load Veusz-SVG'
    description_short = 'Load Veusz-SVG image.'
    description_full = 'Load re-editable Veusz-SVG image.'

    def __init__(self):
        """Make list of fields."""
        from veusz.plugins import FieldFilename
        self.fields = [
            FieldFilename("filepath", descr="SVG filepath"),
            ]

    def apply(self, interface, fields):
        """Do the work of the plugin.
        interface: veusz command line interface object (exporting commands)
        fields: dict mapping field names to values
        """
        import xml.etree.ElementTree as ET

        # Enable all commands under interface
        cmds = [cmd for cmd in dir(interface) if cmd.startswith('__') is False]
        for cmd in cmds:
            exec(f"{cmd} = interface.{cmd}")

        # get the .svg filepath
        filepath = fields['filepath']
        
        # Import normal SVG
        namespace = r'{https://veusz.github.io/}'
        vszscript = ''
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            veuszdata = root.find(f'./metadata/{namespace}veusz')
            vszscript = veuszdata.get('script')
        except:
            pass

        if vszscript:
            # Wipe existing widgets
            for child in interface.Root.childnames_widgets:
                interface.Remove(child)
            # Exec saved commands
            exec(vszscript)

toolspluginregistry.append(LoadVSZSVGPlugin)