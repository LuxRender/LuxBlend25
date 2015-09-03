# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 LuxRender Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Jens Verwiebe, Jason Clarke, Asbjørn Heid
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
#
# ***** END GPL LICENCE BLOCK *****

import re

import bpy

from ..extensions_framework import declarative_property_group

from .. import LuxRenderAddon
from ..properties import (
    luxrender_texture_node, get_linked_node, check_node_export_texture, check_node_get_paramset
)
from ..properties.texture import (
    import_paramset_to_blender_texture, shorten_name, refresh_preview
)
from ..export import ParamSet, process_filepath_data
from ..export.materials import (
    ExportedTextures, add_texture_parameter, get_texture_from_scene
)
from ..outputs import LuxManager, LuxLog

from ..properties.node_texture import (
    variant_items, triple_variant_items
)

from ..properties.node_material import get_socket_paramsets

from ..properties.node_sockets import (
    luxrender_fresnel_socket, luxrender_TF_amount_socket, luxrender_transform_socket, luxrender_TF_tex1_socket,
    luxrender_TF_tex2_socket, luxrender_TFR_tex1_socket, luxrender_TFR_tex2_socket, luxrender_TC_tex1_socket,
    luxrender_TC_tex2_socket
)

from . import warning_luxcore_node


@LuxRenderAddon.addon_register_class
class luxrender_texture_type_node_add(luxrender_texture_node):
    """Add texture node"""
    bl_idname = 'luxrender_texture_add_node'
    bl_label = 'Add'
    bl_icon = 'TEXTURE'

    variant = bpy.props.EnumProperty(name='Variant', items=variant_items, default='color')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'variant')

        si = self.inputs.keys()
        so = self.outputs.keys()
        if self.variant == 'color':
            if not 'Color 1' in si:  # If there aren't color inputs, create them
                self.inputs.new('luxrender_TC_tex1_socket', 'Color 1')
                self.inputs.new('luxrender_TC_tex2_socket', 'Color 2')

            if 'Float 1' in si:  # If there are float inputs, destory them
                self.inputs.remove(self.inputs['Float 1'])
                self.inputs.remove(self.inputs['Float 2'])

            if not 'Color' in so:  # If there is no color output, create it
                self.outputs.new('NodeSocketColor', 'Color')

            if 'Float' in so:  # If there is a float output, destroy it
                self.outputs.remove(self.outputs['Float'])
        if self.variant == 'float':
            if not 'Float 1' in si:
                self.inputs.new('luxrender_TF_tex1_socket', 'Float 1')
                self.inputs.new('luxrender_TF_tex2_socket', 'Float 2')

            if 'Color 1' in si:
                self.inputs.remove(self.inputs['Color 1'])
                self.inputs.remove(self.inputs['Color 2'])

            if not 'Float' in so:
                self.outputs.new('NodeSocketFloat', 'Float')

            if 'Color' in so:
                self.outputs.remove(self.outputs['Color'])

    def export_texture(self, make_texture):
        addtex_params = ParamSet()
        addtex_params.update(get_socket_paramsets(self.inputs, make_texture))

        return make_texture(self.variant, 'add', self.name, addtex_params)


@LuxRenderAddon.addon_register_class
class luxrender_texture_type_node_bump_map(luxrender_texture_node):
    """Bump map texture node"""
    bl_idname = 'luxrender_texture_bump_map_node'
    bl_label = 'Bump Height'
    bl_icon = 'TEXTURE'
    bl_width_min = 180

    bump_height = bpy.props.FloatProperty(name='Bump Height', description='Height of the bump map', default=.001,
                                          precision=6, subtype='DISTANCE', unit='LENGTH', step=.001)

    def init(self, context):
        self.inputs.new('luxrender_TF_bump_socket', 'Float')
        self.outputs.new('NodeSocketFloat', 'Bump')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'bump_height')

    def export_texture(self, make_texture):
        bumpmap_params = ParamSet() \
            .add_float('tex1', self.bump_height)

        tex_node = get_linked_node(self.inputs[0])

        if tex_node and check_node_export_texture(tex_node):
            bumpmap_name = tex_node.export_texture(make_texture)
            bumpmap_params.add_texture("tex2", bumpmap_name)

        return make_texture('float', 'scale', self.name, bumpmap_params)


@LuxRenderAddon.addon_register_class
class luxrender_texture_type_node_mix(luxrender_texture_node):
    """Mix texture node"""
    bl_idname = 'luxrender_texture_mix_node'
    bl_label = 'Mix'
    bl_icon = 'TEXTURE'
    bl_width_min = 180

    variant = bpy.props.EnumProperty(name='Variant', items=triple_variant_items, default='color')

    def init(self, context):
        self.inputs.new('luxrender_TF_amount_socket', 'Mix Amount')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'variant')

        si = self.inputs.keys()
        so = self.outputs.keys()

        if self.variant == 'color':
            if not 'Color 1' in si:
                self.inputs.new('luxrender_TC_tex1_socket', 'Color 1')
                self.inputs.new('luxrender_TC_tex2_socket', 'Color 2')

            if 'Float 1' in si:
                self.inputs.remove(self.inputs['Float 1'])
                self.inputs.remove(self.inputs['Float 2'])

            if 'IOR 1' in si:
                self.inputs.remove(self.inputs['IOR 1'])
                self.inputs.remove(self.inputs['IOR 2'])

            if not 'Color' in so:
                self.outputs.new('NodeSocketColor', 'Color')

            if 'Float' in so:
                self.outputs.remove(self.outputs['Float'])

            if 'IOR' in so:
                self.outputs.remove(self.outputs['IOR'])

        if self.variant == 'float':
            if not 'Float 1' in si:
                self.inputs.new('luxrender_TF_tex1_socket', 'Float 1')
                self.inputs.new('luxrender_TF_tex2_socket', 'Float 2')

            if 'Color 1' in si:
                self.inputs.remove(self.inputs['Color 1'])
                self.inputs.remove(self.inputs['Color 2'])

            if 'IOR 1' in si:
                self.inputs.remove(self.inputs['IOR 1'])
                self.inputs.remove(self.inputs['IOR 2'])

            if not 'Float' in so:
                self.outputs.new('NodeSocketFloat', 'Float')

            if 'Color' in so:
                self.outputs.remove(self.outputs['Color'])

            if 'IOR' in so:
                self.outputs.remove(self.outputs['IOR'])

        if self.variant == 'fresnel':
            if not 'IOR 1' in si:
                self.inputs.new('luxrender_TFR_tex1_socket', 'IOR 1')
                self.inputs.new('luxrender_TFR_tex2_socket', 'IOR 2')

            if 'Color 1' in si:
                self.inputs.remove(self.inputs['Color 1'])
                self.inputs.remove(self.inputs['Color 2'])

            if 'Float 1' in si:
                self.inputs.remove(self.inputs['Float 1'])
                self.inputs.remove(self.inputs['Float 2'])

            if not 'IOR' in so:
                self.outputs.new('luxrender_fresnel_output_socket', 'IOR')

            if 'Color' in so:
                self.outputs.remove(self.outputs['Color'])

            if 'Float' in so:
                self.outputs.remove(self.outputs['Float'])

    def export_texture(self, make_texture):
        mix_params = ParamSet()
        mix_params.update(get_socket_paramsets(self.inputs, make_texture))

        return make_texture(self.variant, 'mix', self.name, mix_params)


@LuxRenderAddon.addon_register_class
class luxrender_texture_type_node_scale(luxrender_texture_node):
    """Scale texture node"""
    bl_idname = 'luxrender_texture_scale_node'
    bl_label = 'Scale'
    bl_icon = 'TEXTURE'

    variant = bpy.props.EnumProperty(name='Variant', items=variant_items, default='color')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'variant')

        si = self.inputs.keys()
        so = self.outputs.keys()

        if self.variant == 'color':
            if not 'Color 1' in si:
                self.inputs.new('luxrender_TC_tex1_socket', 'Color 1')
                self.inputs.new('luxrender_TC_tex2_socket', 'Color 2')

            if 'Float 1' in si:
                self.inputs.remove(self.inputs['Float 1'])
                self.inputs.remove(self.inputs['Float 2'])

            if not 'Color' in so:
                self.outputs.new('NodeSocketColor', 'Color')

            if 'Float' in so:
                self.outputs.remove(self.outputs['Float'])
        if self.variant == 'float':
            if not 'Float 1' in si:
                self.inputs.new('luxrender_TF_tex1_socket', 'Float 1')
                self.inputs.new('luxrender_TF_tex2_socket', 'Float 2')

            if 'Color 1' in si:
                self.inputs.remove(self.inputs['Color 1'])
                self.inputs.remove(self.inputs['Color 2'])

            if not 'Float' in so:
                self.outputs.new('NodeSocketFloat', 'Float')

            if 'Color' in so:
                self.outputs.remove(self.outputs['Color'])

    def export_texture(self, make_texture):
        scale_params = ParamSet()
        scale_params.update(get_socket_paramsets(self.inputs, make_texture))

        return make_texture(self.variant, 'scale', self.name, scale_params)


@LuxRenderAddon.addon_register_class
class luxrender_texture_type_node_subtract(luxrender_texture_node):
    """Subtract texture node"""
    bl_idname = 'luxrender_texture_subtract_node'
    bl_label = 'Subtract'
    bl_icon = 'TEXTURE'

    variant = bpy.props.EnumProperty(name='Variant', items=variant_items, default='color')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'variant')

        si = self.inputs.keys()
        so = self.outputs.keys()
        if self.variant == 'color':
            if not 'Color 1' in si:
                self.inputs.new('luxrender_TC_tex1_socket', 'Color 1')
                self.inputs.new('luxrender_TC_tex2_socket', 'Color 2')

            if 'Float 1' in si:
                self.inputs.remove(self.inputs['Float 1'])
                self.inputs.remove(self.inputs['Float 2'])

            if not 'Color' in so:
                self.outputs.new('NodeSocketColor', 'Color')

            if 'Float' in so:
                self.outputs.remove(self.outputs['Float'])

        if self.variant == 'float':
            if not 'Float 1' in si:
                self.inputs.new('luxrender_TF_tex1_socket', 'Float 1')
                self.inputs.new('luxrender_TF_tex2_socket', 'Float 2')

            if 'Color 1' in si:
                self.inputs.remove(self.inputs['Color 1'])
                self.inputs.remove(self.inputs['Color 2'])

            if not 'Float' in so:
                self.outputs.new('NodeSocketFloat', 'Float')

            if 'Color' in so:
                self.outputs.remove(self.outputs['Color'])

    def export_texture(self, make_texture):
        subtract_params = ParamSet()
        subtract_params.update(get_socket_paramsets(self.inputs, make_texture))

        return make_texture(self.variant, 'subtract', self.name, subtract_params)


@LuxRenderAddon.addon_register_class
class luxrender_texture_type_node_colordepth(luxrender_texture_node):
    """Color at Depth node"""
    bl_idname = 'luxrender_texture_colordepth_node'
    bl_label = 'Color at Depth'
    bl_icon = 'TEXTURE'

    depth = bpy.props.FloatProperty(name='Depth', default=1.0, subtype='DISTANCE', unit='LENGTH')

    def init(self, context):
        self.inputs.new('luxrender_TC_Kt_socket', 'Transmission Color')
        self.outputs.new('NodeSocketColor', 'Color')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'depth')

    def export_texture(self, make_texture):
        colordepth_params = ParamSet()
        colordepth_params.update(get_socket_paramsets(self.inputs, make_texture))
        colordepth_params.add_float('depth', self.depth)

        return make_texture('color', 'colordepth', self.name, colordepth_params)


@LuxRenderAddon.addon_register_class
class luxrender_texture_type_node_colorramp(luxrender_texture_node):
    """Colorramp texture node"""
    bl_idname = 'luxrender_texture_colorramp_node'
    bl_label = 'ColorRamp'
    bl_icon = 'TEXTURE'
    bl_width_min = 260

    @classmethod
    def poll(cls, node_tree):
        return node_tree is not None

    def get_fake_texture(self):
        name = self.name

        if name not in bpy.data.textures:
            fake_texture = bpy.data.textures.new(name=name, type='NONE')
            # Set fake user so the texture is not deleted on Blender close
            fake_texture.use_fake_user = True
            fake_texture.use_color_ramp = True
            # Set alpha from default 0 to 1
            fake_texture.color_ramp.elements[0].color[3] = 1.0

        return bpy.data.textures[name]

    def draw_buttons(self, context, layout):
        warning_luxcore_node(layout)

        si = self.inputs.keys()
        so = self.outputs.keys()

        if not 'Amount' in si:
            self.inputs.new('luxrender_TF_amount_socket', 'Amount')

        if not 'Color' in so:
            self.outputs.new('NodeSocketColor', 'Color')

        fake_texture = self.get_fake_texture()
        layout.template_color_ramp(fake_texture, "color_ramp", expand=True)
