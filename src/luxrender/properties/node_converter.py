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

from . import warning_luxcore_node, create_luxcore_name, set_prop_tex


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

            if 'Fresnel' in so:
                self.outputs.remove(self.outputs['Fresnel'])

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

            if 'Fresnel' in so:
                self.outputs.remove(self.outputs['Fresnel'])

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

            if not 'Fresnel' in so:
                self.outputs.new('luxrender_fresnel_socket', 'Fresnel')
                self.outputs['Fresnel'].needs_link = True

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
class luxrender_texture_type_node_math(luxrender_texture_node):
    """Color at Depth node"""
    bl_idname = 'luxrender_texture_math_node'
    bl_label = 'Math'
    bl_icon = 'TEXTURE'

    input_settings = {
        'default': {
            0: ['Value 1', True],
            1: ['Value 2', True],
            2: ['', False]
        },
        'abs': {
            0: ['Value', True], # slot index: [name, enabled]
            1: ['', False],
            2: ['', False]
        },
        'clamp': {
            0: ['Value', True],
            1: ['', False],
            2: ['', False]
        },
        'mix': {
            0: ['Amount', True],
            1: ['Value 1', True],
            2: ['Value 2', True]
        }
    }

    def change_mode(self, context):
        mode = self.mode if self.mode in self.input_settings else 'default'
        current_settings = self.input_settings[mode]

        for i in current_settings.keys():
            self.inputs[i].name = current_settings[i][0]
            self.inputs[i].enabled = current_settings[i][1]

    mode_items = [
        ('scale', 'Multiply', ''),
        ('add', 'Add', ''),
        ('subtract', 'Subtract', ''),
        ('mix', 'Mix', 'Mix between two values/textures according to the amount (0 = use first value, 1 = use second value'),
        ('clamp', 'Clamp', 'Clamp the input so it is between min and max values'),
        ('abs', 'Absolute', 'Take the absolute value (remove minus sign)'),
    ]
    mode = bpy.props.EnumProperty(name='Mode', items=mode_items, default='scale', update=change_mode)

    mode_clamp_min = bpy.props.FloatProperty(name='Min', description='', default=0)
    mode_clamp_max = bpy.props.FloatProperty(name='Max', description='', default=1)

    clamp_output = bpy.props.BoolProperty(name='Clamp', default=False, description='Limit the output value to 0..1 range')

    def init(self, context):
        self.inputs.new('luxrender_float_socket', 'Value 1')
        self.inputs.new('luxrender_float_socket', 'Value 2')
        self.inputs.new('luxrender_float_socket', 'Value 3') # for mix mode
        self.inputs[2].enabled = False

        self.outputs.new('NodeSocketFloat', 'Value')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'mode', text='')
        layout.prop(self, 'clamp_output')

        if self.mode == 'clamp':
            layout.prop(self, 'mode_clamp_min')
            layout.prop(self, 'mode_clamp_max')

    # TODO: classic export

    def export_luxcore(self, properties):
        luxcore_name = create_luxcore_name(self)

        slot_0 = self.inputs[0].export_luxcore(properties)
        slot_1 = self.inputs[1].export_luxcore(properties)
        slot_2 = self.inputs[2].export_luxcore(properties)

        set_prop_tex(properties, luxcore_name, 'type', self.mode)

        if self.mode == 'abs':
            set_prop_tex(properties, luxcore_name, 'texture', slot_0)
        elif self.mode == 'clamp':
            set_prop_tex(properties, luxcore_name, 'texture', slot_0)
            set_prop_tex(properties, luxcore_name, 'min', self.mode_clamp_min)
            set_prop_tex(properties, luxcore_name, 'max', self.mode_clamp_max)
        elif self.mode == 'mix':
            set_prop_tex(properties, luxcore_name, 'amount', slot_0)
            set_prop_tex(properties, luxcore_name, 'texture1', slot_1)
            set_prop_tex(properties, luxcore_name, 'texture2', slot_2)
        else:
            set_prop_tex(properties, luxcore_name, 'texture1', slot_0)
            set_prop_tex(properties, luxcore_name, 'texture2', slot_1)

        if self.clamp_output:
            clamp_name = create_luxcore_name(self, suffix='clamp')
            set_prop_tex(properties, clamp_name, 'type', 'clamp')
            set_prop_tex(properties, clamp_name, 'texture', luxcore_name)
            set_prop_tex(properties, clamp_name, 'min', 0)
            set_prop_tex(properties, clamp_name, 'max', 1)
            luxcore_name = clamp_name

        return luxcore_name


@LuxRenderAddon.addon_register_class
class luxrender_texture_type_node_colormix(luxrender_texture_node):
    """Color at Depth node"""
    bl_idname = 'luxrender_texture_colormix_node'
    bl_label = 'ColorMix'
    bl_icon = 'TEXTURE'

    input_settings = {
        'default': {
            1: ['Color 1', True],
            2: ['Color 2', True]
        },
        'abs': {
            1: ['Color', True], # slot index: [name, enabled]
            2: ['', False]
        },
        'clamp': {
            1: ['Color', True],
            2: ['', False]
        },
        'mix': {
            1: ['Color 1', True],
            2: ['Color 2', True]
        }
    }

    def change_mode(self, context):
        mode = self.mode if self.mode in self.input_settings else 'default'
        current_settings = self.input_settings[mode]

        for i in current_settings.keys():
            self.inputs[i].name = current_settings[i][0]
            self.inputs[i].enabled = current_settings[i][1]

    mode_items = [
        ('scale', 'Multiply', ''),
        ('add', 'Add', ''),
        ('subtract', 'Subtract', ''),
        ('mix', 'Mix', 'Mix between two values/textures according to the amount (0 = use first value, 1 = use second value'),
        ('clamp', 'Clamp', 'Clamp the input so it is between min and max values'),
        ('abs', 'Absolute', 'Take the absolute value (remove minus sign)'),
    ]
    mode = bpy.props.EnumProperty(name='Mode', items=mode_items, default='mix', update=change_mode)

    mode_clamp_min = bpy.props.FloatProperty(name='Min', description='', default=0)
    mode_clamp_max = bpy.props.FloatProperty(name='Max', description='', default=1)

    clamp_output = bpy.props.BoolProperty(name='Clamp', default=False, description='Limit the output value to 0..1 range')

    def init(self, context):
        self.inputs.new('luxrender_TF_amount_socket', 'Fac')
        self.inputs[0].default_value = 1
        self.inputs.new('luxrender_color_socket', 'Color 1')
        self.inputs.new('luxrender_color_socket', 'Color 2')

        self.outputs.new('NodeSocketColor', 'Color')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'mode', text='')
        layout.prop(self, 'clamp_output')

        if self.mode == 'clamp':
            layout.prop(self, 'mode_clamp_min')
            layout.prop(self, 'mode_clamp_max')

    # TODO: classic export

    def export_luxcore(self, properties):
        luxcore_name = create_luxcore_name(self)

        slot_0 = self.inputs[0].export_luxcore(properties)
        slot_1 = self.inputs[1].export_luxcore(properties)
        slot_2 = self.inputs[2].export_luxcore(properties)

        set_prop_tex(properties, luxcore_name, 'type', self.mode)

        if self.mode == 'abs':
            set_prop_tex(properties, luxcore_name, 'texture', slot_1)
        elif self.mode == 'clamp':
            set_prop_tex(properties, luxcore_name, 'texture', slot_1)
            set_prop_tex(properties, luxcore_name, 'min', self.mode_clamp_min)
            set_prop_tex(properties, luxcore_name, 'max', self.mode_clamp_max)
        elif self.mode == 'mix':
            set_prop_tex(properties, luxcore_name, 'amount', slot_0)
            set_prop_tex(properties, luxcore_name, 'texture1', slot_1)
            set_prop_tex(properties, luxcore_name, 'texture2', slot_2)
        else:
            set_prop_tex(properties, luxcore_name, 'texture1', slot_1)
            set_prop_tex(properties, luxcore_name, 'texture2', slot_2)

        if self.clamp_output:
            clamp_name = create_luxcore_name(self, suffix='clamp')
            set_prop_tex(properties, clamp_name, 'type', 'clamp')
            set_prop_tex(properties, clamp_name, 'texture', luxcore_name)
            set_prop_tex(properties, clamp_name, 'min', 0)
            set_prop_tex(properties, clamp_name, 'max', 1)
            luxcore_name = clamp_name

        if slot_0 != 1 and self.mode != 'mix':
            mix_name = create_luxcore_name(self, suffix='mix')
            set_prop_tex(properties, mix_name, 'type', 'mix')
            set_prop_tex(properties, mix_name, 'amount', slot_0)
            set_prop_tex(properties, mix_name, 'texture1', slot_1)
            set_prop_tex(properties, mix_name, 'texture2', luxcore_name)
            luxcore_name = mix_name

        return luxcore_name


@LuxRenderAddon.addon_register_class
class luxrender_texture_type_node_colorramp(luxrender_texture_node):
    """Colorramp texture node"""
    bl_idname = 'luxrender_texture_colorramp_node'
    bl_label = 'ColorRamp'
    bl_icon = 'TEXTURE'
    bl_width_min = 260

    #TODO: wait for the colorramp property to be exposed by Blender API before releasing this into the wild!

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
