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

import nodeitems_utils
from nodeitems_utils import NodeCategory, NodeItem, NodeItemCustom

from .. import LuxRenderAddon
from ..properties import (luxrender_node, luxrender_material_node, get_linked_node, check_node_export_material,
                          check_node_export_texture, check_node_get_paramset, ExportedVolumes)

from ..properties.texture import (
    import_paramset_to_blender_texture, shorten_name, refresh_preview
)
from ..export import ParamSet, process_filepath_data
from ..export.materials import (
    MaterialCounter, TextureCounter, ExportedMaterials, ExportedTextures, get_texture_from_scene
)

from ..outputs import LuxManager, LuxLog
from ..outputs.luxcore_api import UseLuxCore, pyluxcore, ToValidLuxCoreName

from ..properties.node_sockets import *

from . import (set_prop_mat, set_prop_vol, create_luxcore_name_mat, create_luxcore_name_vol, export_submat_luxcore,
               export_emission_luxcore, warning_classic_node, warning_luxcore_node)


class luxrender_texture_maker:
    def __init__(self, lux_context, root_name):
        def _impl(tex_variant, tex_type, tex_name, tex_params):
            nonlocal lux_context
            texture_name = '%s::%s' % (root_name, tex_name)

            with TextureCounter(texture_name):
                print('Exporting texture, variant: "%s", type: "%s", name: "%s"' % (tex_variant, tex_type, tex_name))

                ExportedTextures.texture(lux_context, texture_name, tex_variant, tex_type, tex_params)
                ExportedTextures.export_new(lux_context)

                return texture_name

        self.make_texture = _impl


def get_socket_paramsets(sockets, make_texture):
    params = ParamSet()

    for socket in sockets:
        if not hasattr(socket, 'get_paramset'):
            print('No get_paramset() for socket %s' % socket.bl_idname)
            continue

        if not socket.enabled:
            print('Disabled socket %s will not be exported' % socket.bl_idname)
            continue

        params.update(socket.get_paramset(make_texture))

    return params


# Material nodes alphabetical
@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_carpaint(luxrender_material_node):
    # Description string
    """Car paint material node"""
    # Optional identifier string. If not explicitly defined, the python class name is used.
    bl_idname = 'luxrender_material_carpaint_node'
    # Label for nice name display
    bl_label = 'Car Paint Material'
    # Icon identifier
    bl_icon = 'MATERIAL'
    bl_width_min = 200

    # Get menu items from old material editor properties
    for prop in luxrender_mat_carpaint.properties:
        if prop['attr'].startswith('name'):
            carpaint_items = prop['items']

    def change_is_preset(self, context):
        # Hide unused params when using presets
        self.inputs['Diffuse Color'].enabled = self.carpaint_presets == '-'
        self.inputs['Specular Color 1'].enabled = self.carpaint_presets == '-'
        self.inputs['Specular Color 2'].enabled = self.carpaint_presets == '-'
        self.inputs['Specular Color 3'].enabled = self.carpaint_presets == '-'
        self.inputs['M1'].enabled = self.carpaint_presets == '-'
        self.inputs['M2'].enabled = self.carpaint_presets == '-'
        self.inputs['M3'].enabled = self.carpaint_presets == '-'
        self.inputs['R1'].enabled = self.carpaint_presets == '-'
        self.inputs['R2'].enabled = self.carpaint_presets == '-'
        self.inputs['R3'].enabled = self.carpaint_presets == '-'

    # Definitions for non-socket properties
    carpaint_presets = bpy.props.EnumProperty(name='Car Paint Presets', description='Luxrender Carpaint Presets',
                                              items=carpaint_items, default='-', update=change_is_preset)

    # Definitions for sockets
    def init(self, context):
        self.inputs.new('luxrender_TC_Kd_socket', 'Diffuse Color')
        self.inputs.new('luxrender_TC_Ks1_socket', 'Specular Color 1')
        self.inputs.new('luxrender_TF_R1_socket', 'R1')
        self.inputs.new('luxrender_TF_M1_socket', 'M1')
        self.inputs.new('luxrender_TC_Ks2_socket', 'Specular Color 2')
        self.inputs.new('luxrender_TF_R2_socket', 'R2')
        self.inputs.new('luxrender_TF_M2_socket', 'M2')
        self.inputs.new('luxrender_TC_Ks3_socket', 'Specular Color 3')
        self.inputs.new('luxrender_TF_R3_socket', 'R3')
        self.inputs.new('luxrender_TF_M3_socket', 'M3')
        self.inputs.new('luxrender_TC_Ka_socket', 'Absorption Color')
        self.inputs.new('luxrender_TF_d_socket', 'Absorption Depth')
        self.inputs.new('luxrender_TF_bump_socket', 'Bump')

        self.outputs.new('NodeSocketShader', 'Surface')

    # Draw the non-socket properties
    def draw_buttons(self, context, layout):
        layout.prop(self, 'carpaint_presets')

    # Export routine for this node. This function stores code that LuxBlend will run when it exports materials.
    def export_material(self, make_material, make_texture):
        mat_type = 'carpaint'

        carpaint_params = ParamSet()
        # have to export the sockets, or else bump/normal mapping won't work when using a preset
        carpaint_params.update(get_socket_paramsets(self.inputs, make_texture))

        if self.carpaint_presets != '-':
            carpaint_params.add_string('name', self.carpaint_presets)

        return make_material(mat_type, self.name, carpaint_params)

    # TODO: LuxCore export


@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_cloth(luxrender_material_node):
    """Cloth material node"""
    bl_idname = 'luxrender_material_cloth_node'
    bl_label = 'Cloth Material'
    bl_icon = 'MATERIAL'
    bl_width_min = 180

    for prop in luxrender_mat_cloth.properties:
        if prop['attr'].startswith('presetname'):
            cloth_items = prop['items']

    fabric_type = bpy.props.EnumProperty(name='Cloth Fabric', description='Luxrender Cloth Fabric', items=cloth_items,
                                         default='denim')
    repeat_u = bpy.props.FloatProperty(name='Repeat U', default=100.0)
    repeat_v = bpy.props.FloatProperty(name='Repeat V', default=100.0)


    def init(self, context):
        self.inputs.new('luxrender_TC_warp_Kd_socket', 'Warp Diffuse Color')
        self.inputs.new('luxrender_TC_warp_Ks_socket', 'Warp Specular Color')
        self.inputs.new('luxrender_TC_weft_Kd_socket', 'Weft Diffuse Color')
        self.inputs.new('luxrender_TC_weft_Ks_socket', 'Weft Specular Color')
        self.inputs.new('luxrender_TF_bump_socket', 'Bump')
        self.outputs.new('NodeSocketShader', 'Surface')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'fabric_type')
        layout.prop(self, 'repeat_u')
        layout.prop(self, 'repeat_v')

    def export_material(self, make_material, make_texture):
        mat_type = 'cloth'

        cloth_params = ParamSet()
        cloth_params.update(get_socket_paramsets(self.inputs, make_texture))

        cloth_params.add_string('presetname', self.fabric_type)
        cloth_params.add_float('repeat_u', self.repeat_u)
        cloth_params.add_float('repeat_v', self.repeat_v)

        return make_material(mat_type, self.name, cloth_params)

    # TODO: LuxCore export


@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_doubleside(luxrender_material_node):
    """Doubel-sided material node"""
    bl_idname = 'luxrender_material_doubleside_node'
    bl_label = 'Double-Sided Material'
    bl_icon = 'MATERIAL'
    bl_width_min = 160

    usefrontforfront = bpy.props.BoolProperty(name='Use front for front',
                                              description='Use front side of front material for front side',
                                              default=True)
    usefrontforback = bpy.props.BoolProperty(name='Use front for back',
                                             description='Use front side of back material for back side', default=True)

    def init(self, context):
        self.inputs.new('NodeSocketShader', 'Front Material')
        self.inputs['Front Material'].name = 'Front Material'
        self.inputs.new('NodeSocketShader', 'Back Material')
        self.inputs['Back Material'].name = 'Back Material'
        self.outputs.new('NodeSocketShader', 'Surface')

    def draw_buttons(self, context, layout):
        warning_classic_node(layout)

        layout.prop(self, 'usefrontforfront')
        layout.prop(self, 'usefrontforback')

    def export_material(self, make_material, make_texture):
        print('export node: doubleside')

        mat_type = 'doubleside'

        doubleside_params = ParamSet()

        def export_submat(socket):
            node = get_linked_node(socket)

            if not check_node_export_material(node):
                return None

            return node.export_material(make_material, make_texture)

        frontmat_name = export_submat(self.inputs[0])

        if self.inputs[1].is_linked:
            backmat_name = export_submat(self.inputs[1])
        else:
            backmat_name = export_submat(self.inputs[0])

        doubleside_params.add_string("frontnamedmaterial", frontmat_name)
        doubleside_params.add_string("backnamedmaterial", backmat_name)
        doubleside_params.add_bool('usefrontforfront', self.usefrontforfront)
        doubleside_params.add_bool('usefrontforback', self.usefrontforback)

        return make_material(mat_type, self.name, doubleside_params)

    # TODO: LuxCore export


@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_glass(luxrender_material_node):
    """Glass material node"""
    bl_idname = 'luxrender_material_glass_node'
    bl_label = 'Glass Material'
    bl_icon = 'MATERIAL'
    bl_width_min = 180

    arch = bpy.props.BoolProperty(name='Architectural',
                                  description='Skips refraction during transmission, propagates alpha and shadow rays',
                                  default=False)

    def init(self, context):
        self.inputs.new('luxrender_TC_Kt_socket', 'Transmission Color')
        self.inputs.new('luxrender_TC_Kr_socket', 'Reflection Color')
        self.inputs.new('luxrender_TF_ior_socket', 'IOR')
        self.inputs.new('luxrender_TF_cauchyb_socket', 'Cauchy B')
        self.inputs.new('luxrender_TF_film_ior_socket', 'Film IOR')
        self.inputs.new('luxrender_TF_film_thick_socket', 'Film Thickness (nm)')
        self.inputs.new('luxrender_TF_bump_socket', 'Bump')

        self.outputs.new('NodeSocketShader', 'Surface')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'arch')

    def export_material(self, make_material, make_texture):
        mat_type = 'glass'

        glass_params = ParamSet()
        glass_params.update(get_socket_paramsets(self.inputs, make_texture))

        glass_params.add_bool('architectural', self.arch)

        return make_material(mat_type, self.name, glass_params)


@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_glass2(luxrender_material_node):
    """Glass2 material node"""
    bl_idname = 'luxrender_material_glass2_node'
    bl_label = 'Glass2 Material'
    bl_icon = 'MATERIAL'
    bl_width_min = 160

    arch = bpy.props.BoolProperty(name='Architectural',
                                  description='Skips refraction during transmission, propagates alpha and shadow rays',
                                  default=False)
    dispersion = bpy.props.BoolProperty(name='Dispersion',
                                        description='Enables chromatic dispersion, volume should have a sufficient \
                                        data for this', default=False)

    def init(self, context):
        self.inputs.new('luxrender_TF_bump_socket', 'Bump')

        self.outputs.new('NodeSocketShader', 'Surface')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'arch')
        layout.prop(self, 'dispersion')

    def export_material(self, make_material, make_texture):
        mat_type = 'glass2'

        glass2_params = ParamSet()

        glass2_params.add_bool('architectural', self.arch)
        glass2_params.add_bool('dispersion', self.dispersion)

        return make_material(mat_type, self.name, glass2_params)


@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_glossy(luxrender_material_node):
    """Glossy material node"""
    bl_idname = 'luxrender_material_glossy_node'
    bl_label = 'Glossy Material'
    bl_icon = 'MATERIAL'
    bl_width_min = 180

    def change_use_ior(self, context):
        # # Specular/IOR representation switches
        self.inputs['Specular Color'].enabled = not self.use_ior
        self.inputs['IOR'].enabled = self.use_ior

    def change_use_anisotropy(self, context):
        try:
            self.inputs['Roughness'].sync_vroughness = not self.use_anisotropy
            self.inputs['Roughness'].name = 'Roughness' if not self.use_anisotropy else 'U-Roughness'
        except:
            self.inputs['U-Roughness'].sync_vroughness = not self.use_anisotropy
            self.inputs['U-Roughness'].name = 'Roughness' if not self.use_anisotropy else 'U-Roughness'

        self.inputs['V-Roughness'].enabled = self.use_anisotropy

    multibounce = bpy.props.BoolProperty(name='Multibounce', description='Enable surface layer multibounce',
                                         default=False)
    use_ior = bpy.props.BoolProperty(name='Use IOR', description='Set specularity by IOR', default=False,
                                     update=change_use_ior)
    use_anisotropy = bpy.props.BoolProperty(name='Anisotropic Roughness', description='Anisotropic Roughness',
                                            default=False, update=change_use_anisotropy)

    def init(self, context):
        self.inputs.new('luxrender_TC_Kd_socket', 'Diffuse Color')
        self.inputs.new('luxrender_TF_sigma_socket', 'Sigma')
        self.inputs.new('luxrender_TC_Ks_socket', 'Specular Color')
        self.inputs.new('luxrender_TF_ior_socket', 'IOR')
        self.inputs['IOR'].enabled = False  # initial state is disabled
        self.inputs.new('luxrender_TC_Ka_socket', 'Absorption Color')
        self.inputs.new('luxrender_TF_d_socket', 'Absorption Depth (nm)')
        self.inputs.new('luxrender_TF_uroughness_socket', 'U-Roughness')
        self.inputs.new('luxrender_TF_vroughness_socket', 'V-Roughness')
        self.inputs['V-Roughness'].enabled = False  # initial state is disabled
        self.inputs.new('luxrender_TF_bump_socket', 'Bump')

        self.inputs['U-Roughness'].name = 'Roughness'
        self.outputs.new('NodeSocketShader', 'Surface')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'multibounce')
        layout.prop(self, 'use_ior')
        layout.prop(self, 'use_anisotropy')

    def export_material(self, make_material, make_texture):
        mat_type = 'glossy'

        glossy_params = ParamSet()
        glossy_params.update(get_socket_paramsets(self.inputs, make_texture))

        glossy_params.add_bool('multibounce', self.multibounce)

        return make_material(mat_type, self.name, glossy_params)


@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_glossycoating(luxrender_material_node):
    """Glossy Coating material node"""
    bl_idname = 'luxrender_material_glossycoating_node'
    bl_label = 'Glossy Coating Material'
    bl_icon = 'MATERIAL'
    bl_width_min = 180

    def change_use_ior(self, context):
        # # Specular/IOR representation switches
        self.inputs['Specular Color'].enabled = not self.use_ior
        self.inputs['IOR'].enabled = self.use_ior

    def change_use_anisotropy(self, context):
        try:
            self.inputs['Roughness'].sync_vroughness = not self.use_anisotropy
            self.inputs['Roughness'].name = 'Roughness' if not self.use_anisotropy else 'U-Roughness'
        except:
            self.inputs['U-Roughness'].sync_vroughness = not self.use_anisotropy
            self.inputs['U-Roughness'].name = 'Roughness' if not self.use_anisotropy else 'U-Roughness'

        self.inputs['V-Roughness'].enabled = self.use_anisotropy

    def change_advanced(self, context):
        self.inputs['IOR'].enabled &= self.advanced
        self.inputs['Absorption Color'].enabled = self.advanced
        self.inputs['Absorption Depth (nm)'].enabled = self.advanced

    advanced = bpy.props.BoolProperty(name='Advanced Options', description='Configure advanced options',
                                         default=False, update=change_advanced)
    multibounce = bpy.props.BoolProperty(name='Multibounce', description='Creates a fuzzy, dusty appearance',
                                         default=False)
    use_ior = bpy.props.BoolProperty(name='Use IOR', description='Set specularity by IOR', default=False,
                                     update=change_use_ior)
    use_anisotropy = bpy.props.BoolProperty(name='Anisotropic Roughness', description='Anisotropic Roughness',
                                            default=False, update=change_use_anisotropy)

    def init(self, context):
        self.inputs.new('NodeSocketShader', 'Base Material')
        self.inputs.new('luxrender_TC_Ks_socket', 'Specular Color')
        self.inputs.new('luxrender_TF_ior_socket', 'IOR')
        self.inputs['IOR'].enabled = False  # initial state is disabled
        self.inputs.new('luxrender_TC_Ka_socket', 'Absorption Color')
        self.inputs.new('luxrender_TF_d_socket', 'Absorption Depth (nm)')
        self.inputs.new('luxrender_TF_uroughness_socket', 'U-Roughness')
        self.inputs.new('luxrender_TF_vroughness_socket', 'V-Roughness')
        self.inputs['V-Roughness'].enabled = False  # initial state is disabled
        self.inputs.new('luxrender_TF_bump_socket', 'Bump')

        self.inputs['U-Roughness'].name = 'Roughness'
        self.outputs.new('NodeSocketShader', 'Surface')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'advanced', toggle=True)

        if self.advanced:
            layout.prop(self, 'multibounce')
            layout.prop(self, 'use_ior')
        layout.prop(self, 'use_anisotropy')

    def export_material(self, make_material, make_texture):
        mat_type = 'glossycoating'

        glossycoating_params = ParamSet()
        glossycoating_params.update(get_socket_paramsets(self.inputs, make_texture))

        glossycoating_params.add_bool('multibounce', self.multibounce)

        def export_submat(socket):
            node = get_linked_node(socket)

            if not check_node_export_material(node):
                return None

            return node.export_material(make_material, make_texture)

        basemat_name = export_submat(self.inputs[0])

        glossycoating_params.add_string("basematerial", basemat_name)

        return make_material(mat_type, self.name, glossycoating_params)

    def export_luxcore(self, properties, name=None):
        luxcore_name = create_luxcore_name_mat(self, name)

        base = export_submat_luxcore(properties, self.inputs['Base Material'])
        ks = self.inputs['Specular Color'].export_luxcore(properties)
        u_roughness = self.inputs['Roughness'].export_luxcore(properties)
        v_roughness = self.inputs['V-Roughness'].export_luxcore(properties) if self.use_anisotropy else u_roughness
        ka = self.inputs['Absorption Color'].export_luxcore(properties)
        d = self.inputs['Absorption Depth (nm)'].export_luxcore(properties)
        index = self.inputs['IOR'].export_luxcore(properties)
        bump = self.inputs['Bump'].export_luxcore(properties)

        set_prop_mat(properties, luxcore_name, 'type', 'glossycoating')
        set_prop_mat(properties, luxcore_name, 'base', base)
        set_prop_mat(properties, luxcore_name, 'ks', ks)
        set_prop_mat(properties, luxcore_name, 'uroughness', u_roughness)
        set_prop_mat(properties, luxcore_name, 'vroughness', v_roughness)
        set_prop_mat(properties, luxcore_name, 'ka', ka)
        set_prop_mat(properties, luxcore_name, 'd', d)
        set_prop_mat(properties, luxcore_name, 'multibounce', self.multibounce)

        if self.use_ior:
            set_prop_mat(properties, luxcore_name, 'index', index)

        if bump:
            set_prop_mat(properties, luxcore_name, 'bumptex', bump)

        return luxcore_name


@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_glossytranslucent(luxrender_material_node):
    """Glossytranslucent material node"""
    bl_idname = 'luxrender_material_glossytranslucent_node'
    bl_label = 'Glossy Translucent Material'
    bl_icon = 'MATERIAL'
    bl_width_min = 180

    def change_use_ior(self, context):
        # # Specular/IOR representation switches
        self.inputs['Specular Color'].enabled = not self.use_ior
        self.inputs['IOR'].enabled = self.use_ior

    def change_use_anisotropy(self, context):
        try:
            self.inputs['Roughness'].sync_vroughness = not self.use_anisotropy
            self.inputs['Roughness'].name = 'Roughness' if not self.use_anisotropy else 'U-Roughness'
        except:
            self.inputs['U-Roughness'].sync_vroughness = not self.use_anisotropy
            self.inputs['U-Roughness'].name = 'Roughness' if not self.use_anisotropy else 'U-Roughness'

        self.inputs['V-Roughness'].enabled = self.use_anisotropy

    multibounce = bpy.props.BoolProperty(name='Multibounce', description='Enable surface layer multibounce',
                                         default=False)
    use_ior = bpy.props.BoolProperty(name='Use IOR', description='Set specularity by IOR', default=False,
                                     update=change_use_ior)
    use_anisotropy = bpy.props.BoolProperty(name='Anisotropic Roughness', description='Anisotropic Roughness',
                                            default=False, update=change_use_anisotropy)

    def init(self, context):
        self.inputs.new('luxrender_TC_Kd_socket', 'Diffuse Color')
        self.inputs.new('luxrender_TC_Kt_socket', 'Transmission Color')
        self.inputs.new('luxrender_TC_Ks_socket', 'Specular Color')
        self.inputs.new('luxrender_TF_ior_socket', 'IOR')
        self.inputs.new('luxrender_TC_Ka_socket', 'Absorption Color')
        self.inputs.new('luxrender_TF_d_socket', 'Absorption Depth (nm)')
        self.inputs.new('luxrender_TF_uroughness_socket', 'U-Roughness')
        self.inputs.new('luxrender_TF_vroughness_socket', 'V-Roughness')
        self.inputs['IOR'].enabled = False  # initial state is disabled
        self.inputs['V-Roughness'].enabled = False  # initial state is disabled
        self.inputs.new('luxrender_TF_bump_socket', 'Bump')

        self.inputs['U-Roughness'].name = 'Roughness'
        self.outputs.new('NodeSocketShader', 'Surface')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'multibounce')
        layout.prop(self, 'use_ior')
        layout.prop(self, 'use_anisotropy')

    def export_material(self, make_material, make_texture):
        mat_type = 'glossytranslucent'

        glossytranslucent_params = ParamSet()
        glossytranslucent_params.update(get_socket_paramsets(self.inputs, make_texture))

        glossytranslucent_params.add_bool('multibounce', self.multibounce)

        return make_material(mat_type, self.name, glossytranslucent_params)


@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_layered(luxrender_material_node):
    """Layered material node"""
    bl_idname = 'luxrender_material_layered_node'
    bl_label = 'Layered Material'
    bl_icon = 'MATERIAL'
    bl_width_min = 160

    def init(self, context):
        self.inputs.new('NodeSocketShader', 'Material 1')
        self.inputs.new('luxrender_TF_OP1_socket', 'Opacity 1')
        self.inputs.new('NodeSocketShader', 'Material 2')
        self.inputs.new('luxrender_TF_OP2_socket', 'Opacity 2')
        self.inputs.new('NodeSocketShader', 'Material 3')
        self.inputs.new('luxrender_TF_OP3_socket', 'Opacity 3')
        self.inputs.new('NodeSocketShader', 'Material 4')
        self.inputs.new('luxrender_TF_OP4_socket', 'Opacity 4')

        self.outputs.new('NodeSocketShader', 'Surface')

    def draw_buttons(self, context, layout):
        warning_classic_node(layout)

    def export_material(self, make_material, make_texture):
        print('export node: layered')

        mat_type = 'layered'

        layered_params = ParamSet()
        layered_params.update(get_socket_paramsets([self.inputs[1]], make_texture))
        layered_params.update(get_socket_paramsets([self.inputs[3]], make_texture))
        layered_params.update(get_socket_paramsets([self.inputs[5]], make_texture))
        layered_params.update(get_socket_paramsets([self.inputs[7]], make_texture))

        def export_submat(socket):
            node = get_linked_node(socket)

            if not check_node_export_material(node):
                return None

            return node.export_material(make_material, make_texture)

        if self.inputs[0].is_linked:
            mat1_name = export_submat(self.inputs[0])
            layered_params.add_string("namedmaterial1", mat1_name)

        if self.inputs[2].is_linked:
            mat2_name = export_submat(self.inputs[2])
            layered_params.add_string("namedmaterial2", mat2_name)

        if self.inputs[4].is_linked:
            mat3_name = export_submat(self.inputs[4])
            layered_params.add_string("namedmaterial3", mat3_name)

        if self.inputs[6].is_linked:
            mat4_name = export_submat(self.inputs[6])
            layered_params.add_string("namedmaterial4", mat4_name)

        return make_material(mat_type, self.name, layered_params)


@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_matte(luxrender_material_node):
    """Matte material node"""
    bl_idname = 'luxrender_material_matte_node'
    bl_label = 'Matte Material'
    bl_icon = 'MATERIAL'
    bl_width_min = 160

    def init(self, context):
        self.inputs.new('luxrender_TC_Kd_socket', 'Diffuse Color')
        self.inputs.new('luxrender_TF_sigma_socket', 'Sigma')
        self.inputs.new('luxrender_TF_bump_socket', 'Bump')
        self.inputs.new('NodeSocketShader', 'Emission')

        self.outputs.new('NodeSocketShader', 'Surface')

    def export_material(self, make_material, make_texture):
        mat_type = 'matte'

        matte_params = ParamSet()
        matte_params.update(get_socket_paramsets(self.inputs, make_texture))

        return make_material(mat_type, self.name, matte_params)

    def export_luxcore(self, properties, name=None):
        luxcore_name = create_luxcore_name_mat(self, name)

        kd = self.inputs[0].export_luxcore(properties)
        sigma = self.inputs[1].export_luxcore(properties)
        bump = self.inputs[2].export_luxcore(properties) # may be None!

        if sigma == 0:
            set_prop_mat(properties, luxcore_name, 'type', 'matte')
        else:
            set_prop_mat(properties, luxcore_name, 'type', 'roughmatte')
            set_prop_mat(properties, luxcore_name, 'sigma', sigma)

        set_prop_mat(properties, luxcore_name, 'kd', kd)

        if bump is not None:
            set_prop_mat(properties, luxcore_name, 'bumptex', bump)

        # Light emission
        export_emission_luxcore(properties, self.inputs[3], luxcore_name)

        return luxcore_name


@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_mattetranslucent(luxrender_material_node):
    """Mattetranslucent material node"""
    bl_idname = 'luxrender_material_mattetranslucent_node'
    bl_label = 'Matte Translucent Material'
    bl_icon = 'MATERIAL'
    bl_width_min = 180

    energyconsrv = bpy.props.BoolProperty(name='Energy Conserving', default=True)

    def init(self, context):
        self.inputs.new('luxrender_TC_Kr_socket', 'Reflection Color')
        self.inputs.new('luxrender_TC_Kt_socket', 'Transmission Color')
        self.inputs.new('luxrender_TF_sigma_socket', 'Sigma')
        self.inputs.new('luxrender_TF_bump_socket', 'Bump')

        self.outputs.new('NodeSocketShader', 'Surface')

    def export_material(self, make_material, make_texture):
        mat_type = 'mattetranslucent'

        mattetranslucent_params = ParamSet()
        mattetranslucent_params.update(get_socket_paramsets(self.inputs, make_texture))
        mattetranslucent_params.add_bool('energyconserving', self.energyconsrv)

        return make_material(mat_type, self.name, mattetranslucent_params)


@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_metal(luxrender_material_node):
    """Metal material node"""
    bl_idname = 'luxrender_material_metal_node'
    bl_label = 'Metal Material'
    bl_icon = 'MATERIAL'
    bl_width_min = 180

    for prop in luxrender_mat_metal.properties:
        if prop['attr'].startswith('name'):
            metal_presets = prop['items']

    def change_use_anisotropy(self, context):
        try:
            self.inputs['Roughness'].sync_vroughness = not self.use_anisotropy
            self.inputs['Roughness'].name = 'Roughness' if not self.use_anisotropy else 'U-Roughness'
        except:
            self.inputs['U-Roughness'].sync_vroughness = not self.use_anisotropy
            self.inputs['U-Roughness'].name = 'Roughness' if not self.use_anisotropy else 'U-Roughness'

        self.inputs['V-Roughness'].enabled = self.use_anisotropy

    metal_preset = bpy.props.EnumProperty(name='Preset', description='Luxrender Metal Preset', items=metal_presets,
                                          default='aluminium')

    use_anisotropy = bpy.props.BoolProperty(name='Anisotropic Roughness', description='Anisotropic roughness',
                                            default=False, update=change_use_anisotropy)
    metal_nkfile = bpy.props.StringProperty(name='Nk File', description='Nk file path', subtype='FILE_PATH')

    def init(self, context):
        self.inputs.new('luxrender_TF_uroughness_socket', 'U-Roughness')
        self.inputs.new('luxrender_TF_vroughness_socket', 'V-Roughness')
        self.inputs['V-Roughness'].enabled = False  # initial state is disabled
        self.inputs.new('luxrender_TF_bump_socket', 'Bump')

        self.inputs['U-Roughness'].name = 'Roughness'
        self.outputs.new('NodeSocketShader', 'Surface')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'metal_preset')

        if self.metal_preset == 'nk':
            layout.prop(self, 'metal_nkfile')

        layout.prop(self, 'use_anisotropy')

    def export_material(self, make_material, make_texture):
        print('export node: metal')

        mat_type = 'metal'

        metal_params = ParamSet()
        metal_params.update(get_socket_paramsets(self.inputs, make_texture))

        if self.metal_preset == 'nk':  # use an NK data file
            # This function resolves relative paths (even in linked library blends)
            # and optionally encodes/embeds the data if the setting is enabled
            process_filepath_data(LuxManager.CurrentScene, self, self.metal_nkfile, metal_params, 'filename')
        else:
            # use a preset name
            metal_params.add_string('name', self.metal_preset)

        return make_material(mat_type, self.name, metal_params)


@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_metal2(luxrender_material_node):
    """Metal2 material node"""
    bl_idname = 'luxrender_material_metal2_node'
    bl_label = 'Metal2 Material'
    bl_icon = 'MATERIAL'
    bl_width_min = 180

    #for prop in luxrender_mat_metal2.properties:
    #    if prop['attr'].startswith('metaltype'):
    #        metal2_types = prop['items']

    def change_use_anisotropy(self, context):
        try:
            self.inputs['Roughness'].sync_vroughness = not self.use_anisotropy
            self.inputs['Roughness'].name = 'Roughness' if not self.use_anisotropy else 'U-Roughness'
        except:
            self.inputs['U-Roughness'].sync_vroughness = not self.use_anisotropy
            self.inputs['U-Roughness'].name = 'Roughness' if not self.use_anisotropy else 'U-Roughness'

        self.inputs['V-Roughness'].enabled = self.use_anisotropy

    # metal2_type = bpy.props.EnumProperty(name='Type', description='Luxrender Metal2 Type', items=metal2_types, default='preset')

    for prop in luxrender_mat_metal2.properties:
        if prop['attr'].startswith('preset'):
            metal2_presets = prop['items']
    metal2_preset = bpy.props.EnumProperty(name='Preset', description='Luxrender Metal2 Preset', items=metal2_presets,
                                           default='aluminium')

    # metal2_nkfile = bpy.props.StringProperty(name='Nk File', description='Nk file path', subtype='FILE_PATH')

    input_type_items = [
        ('preset', 'Preset', 'Use pre-configured presets'),
        ('color', 'Color', 'Use custom color as input'),
        ('fresnel', 'Fresnel', 'Use a fresnel texture as input')
    ]
    input_type = bpy.props.EnumProperty(name='Type', description='Input Type', items=input_type_items, default='preset')

    use_anisotropy = bpy.props.BoolProperty(name='Anisotropic Roughness', description='Anisotropic Roughness',
                                            default=False, update=change_use_anisotropy)

    def init(self, context):
        self.inputs.new('luxrender_fresnel_socket', 'Fresnel')
        self.inputs['Fresnel'].needs_link = True  # suppress inappropiate chooser
        self.inputs.new('luxrender_TF_uroughness_socket', 'U-Roughness')
        self.inputs.new('luxrender_TF_vroughness_socket', 'V-Roughness')
        self.inputs['V-Roughness'].enabled = False  # initial state is disabled
        self.inputs.new('luxrender_TF_bump_socket', 'Bump')

        self.inputs['U-Roughness'].name = 'Roughness'
        self.outputs.new('NodeSocketShader', 'Surface')

    def draw_buttons(self, context, layout):
        # layout.prop(self, 'metal2_type')
        # if self.metal2_type == 'preset':
        # layout.prop(self, 'metal2_preset')
        # if self.metal2_type == 'nk':
        # layout.prop(self, 'metal2_nkfile')
        layout.prop(self, 'use_anisotropy')
        layout.prop(self, 'input_type', expand=True)

        if self.input_type == 'preset':
            layout.prop(self, 'metal2_preset')
            if 'Fresnel' in self.inputs:
                self.inputs.remove(self.inputs['Fresnel'])
            if 'Color' in self.inputs:
                self.inputs.remove(self.inputs['Color'])

        elif self.input_type == 'color':
            if 'Fresnel' in self.inputs:
                self.inputs.remove(self.inputs['Fresnel'])
            if not 'Color' in self.inputs:
                self.inputs.new('NodeSocketColor', 'Color')

        elif self.input_type == 'fresnel':
            if 'Color' in self.inputs:
                self.inputs.remove(self.inputs['Color'])
            if not 'Fresnel' in self.inputs:
                self.inputs.new('luxrender_fresnel_socket', 'Fresnel')
                self.inputs['Fresnel'].needs_link = True

    def export_material(self, make_material, make_texture):
        mat_type = 'metal2'

        metal2_params = ParamSet()
        metal2_params.update(get_socket_paramsets(self.inputs, make_texture))

        return make_material(mat_type, self.name, metal2_params)

    def export_luxcore(self, properties, name=None):
        luxcore_name = create_luxcore_name_mat(self, name)

        u_roughness = self.inputs[1].export_luxcore(properties)
        v_roughness = self.inputs[2].export_luxcore(properties) if self.use_anisotropy else u_roughness

        set_prop_mat(properties, luxcore_name, 'type', 'metal2')
        #set_prop_mat(properties, luxcore_name, 'fresnel', )
        set_prop_mat(properties, luxcore_name, 'uroughness', u_roughness)
        set_prop_mat(properties, luxcore_name, 'vroughness', v_roughness)

        return luxcore_name


@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_mirror(luxrender_material_node):
    """Mirror material node"""
    bl_idname = 'luxrender_material_mirror_node'
    bl_label = 'Mirror Material'
    bl_icon = 'MATERIAL'
    bl_width_min = 180

    def init(self, context):
        self.inputs.new('luxrender_TC_Kr_socket', 'Reflection Color')
        self.inputs.new('luxrender_TF_film_ior_socket', 'Film IOR')
        self.inputs.new('luxrender_TF_film_thick_socket', 'Film Thickness (nm)')
        self.inputs.new('luxrender_TF_bump_socket', 'Bump')

        self.outputs.new('NodeSocketShader', 'Surface')

    def export_material(self, make_material, make_texture):
        mat_type = 'mirror'

        mirror_params = ParamSet()
        mirror_params.update(get_socket_paramsets(self.inputs, make_texture))

        return make_material(mat_type, self.name, mirror_params)


@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_mix(luxrender_material_node):
    """Mix material node"""
    bl_idname = 'luxrender_material_mix_node'
    bl_label = 'Mix Material'
    bl_icon = 'MATERIAL'
    bl_width_min = 160

    def init(self, context):
        self.inputs.new('luxrender_TF_amount_socket', 'Mix Amount')
        self.inputs.new('NodeSocketShader', 'Material 1')
        self.inputs.new('NodeSocketShader', 'Material 2')

        if UseLuxCore():
            # LuxCore supports bumpmapping on the mix material
            self.inputs.new('luxrender_TF_bump_socket', 'Bump')

        self.outputs.new('NodeSocketShader', 'Surface')

    def draw_buttons(self, context, layout):
        # When switching from Classic to LuxCore API, add the bump socket. Don't remove it when switching back so
        # node connections are not destroyed, the bump slot will simply be ignored by the Classic API export
        if UseLuxCore():
            if not 'Bump' in self.inputs.keys():
                self.inputs.new('luxrender_TF_bump_socket', 'Bump')

    def export_material(self, make_material, make_texture):
        print('export node: mix')

        mat_type = 'mix'

        mix_params = ParamSet()
        mix_params.update(get_socket_paramsets([self.inputs[0]], make_texture))

        def export_submat(socket):
            node = get_linked_node(socket)

            if not check_node_export_material(node):
                return None

            return node.export_material(make_material, make_texture)

        mat1_name = export_submat(self.inputs[1])
        mat2_name = export_submat(self.inputs[2])

        mix_params.add_string("namedmaterial1", mat1_name)
        mix_params.add_string("namedmaterial2", mat2_name)

        return make_material(mat_type, self.name, mix_params)

    def export_luxcore(self, properties, name=None):
        luxcore_name = create_luxcore_name_mat(self, name)

        amount = self.inputs[0].export_luxcore(properties)
        mat1 = export_submat_luxcore(properties, self.inputs[1])
        mat2 = export_submat_luxcore(properties, self.inputs[2])
        bump = self.inputs[3].export_luxcore(properties) # may be None!

        set_prop_mat(properties, luxcore_name, 'type', 'mix')
        set_prop_mat(properties, luxcore_name, 'amount', amount)
        set_prop_mat(properties, luxcore_name, 'material1', mat1)
        set_prop_mat(properties, luxcore_name, 'material2', mat2)
        if bump:
            set_prop_mat(properties, luxcore_name, 'bumptex', bump)

        return luxcore_name


@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_null(luxrender_material_node):
    """Null material node"""
    bl_idname = 'luxrender_material_null_node'
    bl_label = 'Null Material'
    bl_icon = 'MATERIAL'
    bl_width_min = 160

    def init(self, context):
        self.outputs.new('NodeSocketShader', 'Surface')

    def export_material(self, make_material, make_texture):
        mat_type = 'null'

        null_params = ParamSet()

        return make_material(mat_type, self.name, null_params)

    def export_luxcore(self, properties, name=None):
        luxcore_name = create_luxcore_name_mat(self, name)

        set_prop_mat(properties, luxcore_name, 'type', 'null')

        return luxcore_name


@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_roughglass(luxrender_material_node):
    """Rough Glass material node"""
    bl_idname = 'luxrender_material_roughglass_node'
    bl_label = 'Rough Glass Material'
    bl_icon = 'MATERIAL'
    bl_width_min = 180

    def change_use_anisotropy(self, context):
        try:
            self.inputs['Roughness'].sync_vroughness = not self.use_anisotropy
            self.inputs['Roughness'].name = 'Roughness' if not self.use_anisotropy else 'U-Roughness'
        except:
            self.inputs['U-Roughness'].sync_vroughness = not self.use_anisotropy
            self.inputs['U-Roughness'].name = 'Roughness' if not self.use_anisotropy else 'U-Roughness'

        self.inputs['V-Roughness'].enabled = self.use_anisotropy

    use_anisotropy = bpy.props.BoolProperty(name='Anisotropic Roughness', description='Anisotropic Roughness',
                                            default=False, update=change_use_anisotropy)
    dispersion = bpy.props.BoolProperty(name='Dispersion',
                                        description='Enables chromatic dispersion, Cauchy B value should be none-zero',
                                        default=False)

    def init(self, context):
        self.inputs.new('luxrender_TC_Kt_socket', 'Transmission Color')
        self.inputs.new('luxrender_TC_Kr_socket', 'Reflection Color')
        self.inputs.new('luxrender_TF_ior_socket', 'IOR')
        self.inputs.new('luxrender_TF_cauchyb_socket', 'Cauchy B')
        self.inputs.new('luxrender_TF_uroughness_socket', 'U-Roughness')
        self.inputs.new('luxrender_TF_vroughness_socket', 'V-Roughness')
        self.inputs['V-Roughness'].enabled = False  # initial state is disabled
        self.inputs.new('luxrender_TF_bump_socket', 'Bump')

        self.inputs['U-Roughness'].name = 'Roughness'
        self.outputs.new('NodeSocketShader', 'Surface')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'use_anisotropy')
        layout.prop(self, 'dispersion')

    def export_material(self, make_material, make_texture):
        mat_type = 'roughglass'

        roughglass_params = ParamSet()
        roughglass_params.update(get_socket_paramsets(self.inputs, make_texture))

        roughglass_params.add_bool('dispersion', self.dispersion)

        return make_material(mat_type, self.name, roughglass_params)


@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_scatter(luxrender_material_node):
    """Scatter material node"""
    bl_idname = 'luxrender_material_scatter_node'
    bl_label = 'Scatter Material'
    bl_icon = 'MATERIAL'
    bl_width_min = 160

    def init(self, context):
        self.inputs.new('luxrender_TC_Kd_socket', 'Diffuse Color')
        self.inputs.new('luxrender_SC_asymmetry_socket', 'Asymmetry')

        self.outputs.new('NodeSocketShader', 'Surface')

    def draw_buttons(self, context, layout):
        warning_classic_node(layout)

    def export_material(self, make_material, make_texture):
        mat_type = 'scatter'

        scatter_params = ParamSet()
        scatter_params.update(get_socket_paramsets(self.inputs, make_texture))

        return make_material(mat_type, self.name, scatter_params)


@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_shinymetal(luxrender_material_node):
    """Shiny metal material node"""
    bl_idname = 'luxrender_material_shinymetal_node'
    bl_label = 'Shiny Metal Material'
    bl_icon = 'MATERIAL'
    bl_width_min = 180

    def change_use_anisotropy(self, context):
        try:
            self.inputs['Roughness'].sync_vroughness = not self.use_anisotropy
            self.inputs['Roughness'].name = 'Roughness' if not self.use_anisotropy else 'U-Roughness'
        except:
            self.inputs['U-Roughness'].sync_vroughness = not self.use_anisotropy
            self.inputs['U-Roughness'].name = 'Roughness' if not self.use_anisotropy else 'U-Roughness'

        self.inputs['V-Roughness'].enabled = self.use_anisotropy

    use_anisotropy = bpy.props.BoolProperty(name='Anisotropic Roughness', description='Anisotropic Roughness',
                                            default=False, update=change_use_anisotropy)

    def init(self, context):
        self.inputs.new('luxrender_TC_Kr_socket', 'Reflection Color')
        self.inputs.new('luxrender_TC_Ks_socket', 'Specular Color')
        self.inputs.new('luxrender_TF_film_ior_socket', 'Film IOR')
        self.inputs.new('luxrender_TF_film_thick_socket', 'Film Thickness (nm)')
        self.inputs.new('luxrender_TF_uroughness_socket', 'U-Roughness')
        self.inputs.new('luxrender_TF_vroughness_socket', 'V-Roughness')
        self.inputs['V-Roughness'].enabled = False  # initial state is disabled
        self.inputs.new('luxrender_TF_bump_socket', 'Bump')

        self.inputs['U-Roughness'].name = 'Roughness'
        self.outputs.new('NodeSocketShader', 'Surface')

    def draw_buttons(self, context, layout):
        warning_classic_node(layout)

        layout.prop(self, 'use_anisotropy')

    def export_material(self, make_material, make_texture):
        mat_type = 'shinymetal'

        shinymetal_params = ParamSet()
        shinymetal_params.update(get_socket_paramsets(self.inputs, make_texture))

        return make_material(mat_type, self.name, shinymetal_params)


@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_velvet(luxrender_material_node):
    """Velvet material node"""
    bl_idname = 'luxrender_material_velvet_node'
    bl_label = 'Velvet Material'
    bl_icon = 'MATERIAL'
    bl_width_min = 160

    def update_advanced(self, context):
        self.inputs['p1'].enabled = self.advanced
        self.inputs['p2'].enabled = self.advanced
        self.inputs['p3'].enabled = self.advanced

    advanced = bpy.props.BoolProperty(name='Advanced Options', description='Advanced Velvet Parameters', default=False,
                                      update=update_advanced)

    def init(self, context):
        self.inputs.new('luxrender_TC_Kd_socket', 'Diffuse Color')
        self.inputs.new('luxrender_float_socket', 'Thickness')
        self.inputs['Thickness'].default_value = 0.1
        self.inputs.new('luxrender_float_socket', 'p1')
        self.inputs['p1'].enabled = False
        self.inputs['p1'].default_value = 2
        self.inputs.new('luxrender_float_socket', 'p2')
        self.inputs['p2'].enabled = False
        self.inputs['p2'].default_value = 10
        self.inputs.new('luxrender_float_socket', 'p3')
        self.inputs['p3'].enabled = False
        self.inputs['p3'].default_value = 2

        self.outputs.new('NodeSocketShader', 'Surface')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'advanced', toggle=True)

    def export_material(self, make_material, make_texture):
        mat_type = 'velvet'

        velvet_params = ParamSet()
        velvet_params.update(get_socket_paramsets(self.inputs, make_texture))

        # Classic Lux does not support textured parameters here, so we just use the socket value
        velvet_params.add_float('thickness', self.inputs['Thickness'].default_value)
        velvet_params.add_float('p1', self.inputs['p1'].default_value)
        velvet_params.add_float('p2', self.inputs['p2'].default_value)
        velvet_params.add_float('p3', self.inputs['p3'].default_value)

        return make_material(mat_type, self.name, velvet_params)

    def export_luxcore(self, properties, name=None):
        luxcore_name = create_luxcore_name_mat(self, name)

        kd = self.inputs['Diffuse Color'].export_luxcore(properties)
        thickness = self.inputs['Thickness'].export_luxcore(properties)
        p1 = self.inputs['p1'].export_luxcore(properties)
        p2 = self.inputs['p2'].export_luxcore(properties)
        p3 = self.inputs['p3'].export_luxcore(properties)

        set_prop_mat(properties, luxcore_name, 'type', 'velvet')
        set_prop_mat(properties, luxcore_name, 'kd', kd)
        set_prop_mat(properties, luxcore_name, 'thickness', thickness)

        if self.advanced:
            set_prop_mat(properties, luxcore_name, 'p1', p1)
            set_prop_mat(properties, luxcore_name, 'p2', p2)
            set_prop_mat(properties, luxcore_name, 'p3', p3)

        # TODO: is bump mapping on velvet suported?
        #set_prop_mat(properties, luxcore_name, 'bump', bump)

        return luxcore_name


@LuxRenderAddon.addon_register_class
class luxrender_volume_type_node_clear(luxrender_material_node):
    """Clear volume node"""
    bl_idname = 'luxrender_volume_clear_node'
    bl_label = 'Clear Volume'
    bl_icon = 'MATERIAL'
    bl_width_min = 160

    def init(self, context):
        self.inputs.new('luxrender_fresnel_socket', 'IOR')
        self.inputs.new('luxrender_AC_absorption_socket', 'Absorption Color')

        self.outputs.new('NodeSocketShader', 'Volume')

    def export_volume(self, make_volume, make_texture):
        vol_type = 'clear'

        clear_params = ParamSet()
        clear_params.update(get_socket_paramsets(self.inputs, make_texture))

        return make_volume(self.name, vol_type, clear_params)

    def export_luxcore(self, properties, name=None):
        luxcore_name = create_luxcore_name_vol(self, name)

        set_prop_vol(properties, luxcore_name, 'type', 'clear')
        set_prop_vol(properties, luxcore_name, 'ior', 1.5)
        set_prop_vol(properties, luxcore_name, 'absorption', [.2, .2, .2])
        #set_prop_vol(properties, luxcore_name, '', )


        '''
        self.properties.Set(pyluxcore.Property(prefix + '.absorption', abs_col))
        self.properties.Set(pyluxcore.Property(prefix + '.type', [volume.type]))
        self.properties.Set(pyluxcore.Property(prefix + '.ior', ior_val))
        self.properties.Set(pyluxcore.Property(prefix + '.priority', volume.priority))
        '''

        return luxcore_name


@LuxRenderAddon.addon_register_class
class luxrender_volume_type_node_homogeneous(luxrender_material_node):
    '''Homogeneous volume node'''
    bl_idname = 'luxrender_volume_homogeneous_node'
    bl_label = 'Homogeneous Volume'
    bl_icon = 'MATERIAL'
    bl_width_min = 160

    def init(self, context):
        self.inputs.new('luxrender_fresnel_socket', 'IOR')
        self.inputs.new('luxrender_SC_absorption_socket', 'Absorption Color')
        self.inputs.new('luxrender_SC_color_socket', 'Scattering Color')
        self.inputs.new('luxrender_SC_asymmetry_socket', 'Asymmetry')

        self.outputs.new('NodeSocketShader', 'Volume')

    def export_volume(self, make_volume, make_texture):
        vol_type = 'homogeneous'

        homogeneous_params = ParamSet()
        homogeneous_params.update(get_socket_paramsets(self.inputs, make_texture))

        return make_volume(self.name, vol_type, homogeneous_params)


@LuxRenderAddon.addon_register_class
class luxrender_volume_type_node_heterogeneous(luxrender_material_node):
    """Heterogeneous volume node"""
    bl_idname = 'luxrender_volume_heterogeneous_node'
    bl_label = 'Heterogeneous Volume'
    bl_icon = 'MATERIAL'
    bl_width_min = 160

    stepsize = bpy.props.FloatProperty(name='Step Size', default=1.0, min=0.0, max=100.0, subtype='DISTANCE',
                                       unit='LENGTH', description='Length of ray marching steps, smaller values \
                                       resolve more detail, but are slower')

    def init(self, context):
        self.inputs.new('luxrender_fresnel_socket', 'IOR')
        self.inputs.new('luxrender_SC_absorption_socket', 'Absorption Color')
        self.inputs.new('luxrender_SC_color_socket', 'Scattering Color')
        self.inputs.new('luxrender_SC_asymmetry_socket', 'Asymmetry')

        self.outputs.new('NodeSocketShader', 'Volume')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'stepsize')

    def export_volume(self, make_volume, make_texture):
        vol_type = 'heterogeneous'

        heterogeneous_params = ParamSet()
        heterogeneous_params.update(get_socket_paramsets(self.inputs, make_texture))
        heterogeneous_params.add_float('stepsize', self.stepsize)

        return make_volume(self.name, vol_type, heterogeneous_params)


@LuxRenderAddon.addon_register_class
class luxrender_light_area_node(luxrender_material_node):
    """Area Light node"""
    bl_idname = 'luxrender_light_area_node'
    bl_label = 'Light Emission'
    bl_icon = 'LAMP'
    bl_width_min = 160

    advanced = bpy.props.BoolProperty(name='Advanced Options', default=False)

    gain = bpy.props.FloatProperty(name='Gain', default=1.0, min=0.0, description='Scaling factor for light intensity')
    power = bpy.props.FloatProperty(name='Power (W)', default=100.0, min=0.0)
    efficacy = bpy.props.FloatProperty(name='Efficacy (lm/W)', default=17.0, min=0.0)
    iesname = bpy.props.StringProperty(name='IES Data', description='IES file path', subtype='FILE_PATH')
    importance = bpy.props.FloatProperty(name='Importance', default=1.0, min=0.0,
                                         description='Shadow ray and light path sampling weight')
    nsamples = bpy.props.IntProperty(name='Shadow Ray Count', default=1, min=1, max=64,
                                     description='Number of shadow samples per intersection')
    luxcore_samples = bpy.props.IntProperty(name='Samples', default=-1, min=-1, max=256,
                                     description='Number of shadow samples per intersection')

    def init(self, context):
        self.inputs.new('luxrender_TC_L_socket', 'Light Color')

        self.outputs.new('NodeSocketShader', 'Emission')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'advanced', toggle=True)
        layout.prop(self, 'gain')

        if self.advanced:
            layout.prop(self, 'power')
            layout.prop(self, 'efficacy')
            layout.prop(self, 'iesname')

            if UseLuxCore():
                layout.prop(self, 'luxcore_samples')
            else:
                layout.prop(self, 'importance')
                layout.prop(self, 'nsamples')

    def export(self, make_texture):
        arealight_params = ParamSet()
        arealight_params.update(get_socket_paramsets(self.inputs, make_texture))
        arealight_params.add_float('gain', self.gain)
        arealight_params.add_float('power', self.power)
        arealight_params.add_float('efficacy', self.efficacy)

        if self.iesname:
            process_filepath_data(LuxManager.CurrentScene, self, self.iesname, arealight_params, 'iesname')

        arealight_params.add_float('importance', self.importance)
        arealight_params.add_integer('nsamples', self.nsamples)

        return 'area', arealight_params

    def export_luxcore(self, properties, parent_luxcore_name):
        emission = self.inputs[0].export_luxcore(properties)

        set_prop_mat(properties, parent_luxcore_name, 'emission', emission)
        set_prop_mat(properties, parent_luxcore_name, 'emission.gain', [self.gain] * 3)
        set_prop_mat(properties, parent_luxcore_name, 'emission.power', self.power)
        set_prop_mat(properties, parent_luxcore_name, 'emission.efficency', self.efficacy)
        set_prop_mat(properties, parent_luxcore_name, 'emission.samples', self.luxcore_samples)
        #set_prop_mat(properties, parent_luxcore_name, 'emission.id', )


@LuxRenderAddon.addon_register_class
class luxrender_material_type_node_standard(luxrender_material_node):
    """Standard material node"""

    # TODO: this thing is just a test for now!
    # This node is an experiment to test if it is possible to merge matte, glossy and maybe the translucent versions

    bl_idname = 'luxrender_material_type_node_standard'
    bl_label = 'Standard Material'
    bl_icon = 'MATERIAL'
    bl_width_min = 160

    def update_glossy(self, context):
        self.inputs['Specular Color'].enabled = self.glossy
        self.inputs['Specular Roughness'].enabled = self.glossy

    glossy = bpy.props.BoolProperty(name='Glossy', description='', default=False, update=update_glossy)
    multibounce = bpy.props.BoolProperty(name='Dusty (Multibounce)', description='', default=False)
    anisotropic = bpy.props.BoolProperty(name='Anisotropic', description='', default=False)

    def init(self, context):
        self.outputs.new('NodeSocketShader', 'Surface')

        self.inputs.new('NodeSocketColor', 'Diffuse Color')
        self.inputs.new('NodeSocketFloat', 'Diffuse Roughness')
        self.inputs.new('NodeSocketColor', 'Specular Color')
        self.inputs['Specular Color'].enabled = False
        self.inputs.new('NodeSocketFloat', 'Specular Roughness')
        self.inputs['Specular Roughness'].enabled = False
        self.inputs.new('luxrender_TF_bump_socket', 'Bump')

    def draw_buttons(self, context, layout):
        layout.prop(self, 'glossy')
        if self.glossy:
            layout.prop(self, 'multibounce')
            layout.prop(self, 'anisotropic')


@LuxRenderAddon.addon_register_class
class luxrender_material_output_node(luxrender_node):
    """Material output node"""
    bl_idname = 'luxrender_material_output_node'
    bl_label = 'Material Output'
    bl_icon = 'MATERIAL'
    bl_width_min = 180

    interior_volume = bpy.props.StringProperty(description='Volume inside of the object with this material')
    exterior_volume = bpy.props.StringProperty(description='Volume outside of the object with this material')

    def init(self, context):
        self.inputs.new('NodeSocketShader', 'Surface')
        self.inputs.new('NodeSocketShader', 'Emission')

    def draw_buttons(self, context, layout):
        layout.label(text='Volumes:')

        layout.prop_search(self, 'interior_volume', context.scene.luxrender_volumes, 'volumes', 'Interior',
                           icon='MOD_FLUIDSIM')
        layout.prop_search(self, 'exterior_volume', context.scene.luxrender_volumes, 'volumes', 'Exterior',
                           icon='MOD_FLUIDSIM')

    def export_luxcore(self, material, properties, blender_scene):
        # Note: volumes are exported in export/luxcore/materials.py (in "parent" function that calls this function)

        tree_name = material.luxrender_material.nodetree
        print('Exporting nodetree', tree_name, 'of material', material.name)

        luxcore_name = export_submat_luxcore(properties, self.inputs[0], material.name)

        # Todo: light emission
        # TODO: LuxCore options (Material ID, samples etc.)

        return luxcore_name

    def export(self, scene, lux_context, material, mode='indirect'):

        print('Exporting node tree, mode: %s' % mode)

        surface_socket = self.inputs[0]  # perhaps by name?
        if not surface_socket.is_linked:
            return set()

        surface_node = surface_socket.links[0].from_node

        tree_name = material.luxrender_material.nodetree

        make_material = None
        if mode == 'indirect':
            # named material exporting
            def make_material_indirect(mat_type, mat_name, mat_params):
                nonlocal lux_context
                nonlocal surface_node
                nonlocal material

                if mat_name != surface_node.name:
                    material_name = '%s::%s' % (tree_name, mat_name)
                else:
                    # this is the root material, don't alter name
                    material_name = material.name

                print('Exporting material "%s", type: "%s", name: "%s"' % (material_name, mat_type, mat_name))
                mat_params.add_string('type', mat_type)

                # DistributedPath compositing. Don't forget these!
                if scene.luxrender_integrator.surfaceintegrator == 'distributedpath':
                    mat_params.update(material.luxrender_material.luxrender_mat_compositing.get_paramset())

                ExportedMaterials.makeNamedMaterial(lux_context, material_name, mat_params)
                ExportedMaterials.export_new_named(lux_context)

                return material_name

            make_material = make_material_indirect
        elif mode == 'direct':
            # direct material exporting
            def make_material_direct(mat_type, mat_name, mat_params):
                nonlocal lux_context
                lux_context.material(mat_type, mat_params)

                if mat_name != surface_node.name:
                    material_name = '%s::%s' % (tree_name, mat_name)
                else:
                    # this is the root material, don't alter name
                    material_name = material.name

                print('Exporting material "%s", type: "%s", name: "%s"' % (material_name, mat_type, mat_name))
                mat_params.add_string('type', mat_type)

                # DistributedPath compositing. Don't forget these!
                if scene.luxrender_integrator.surfaceintegrator == 'distributedpath':
                    mat_params.update(material.luxrender_material.luxrender_mat_compositing.get_paramset())

                ExportedMaterials.makeNamedMaterial(lux_context, material_name, mat_params)
                ExportedMaterials.export_new_named(lux_context)

                return material_name

            make_material = make_material_direct


        # texture exporting, only one way
        make_texture = luxrender_texture_maker(lux_context, tree_name).make_texture

        # start exporting that material...
        with MaterialCounter(material.name):
            if not (mode == 'indirect' and material.name in ExportedMaterials.exported_material_names):
                if check_node_export_material(surface_node):
                    surface_node.export_material(make_material=make_material, make_texture=make_texture)

        # TODO: remove, volumes (with nodes) are now exported from their own output node below
        '''
        # Volumes exporting:
        int_vol_socket = self.inputs[1]
        if int_vol_socket.is_linked:
            int_vol_node = int_vol_socket.links[0].from_node

        ext_vol_socket = self.inputs[2]
        if ext_vol_socket.is_linked:
            ext_vol_node = ext_vol_socket.links[0].from_node

        def make_volume(vol_name, vol_type, vol_params):
            nonlocal lux_context
            vol_name = '%s::%s' % (tree_name, vol_name)
            volume_name = vol_name

            # # Here we look for redundant volume definitions caused by material used more than once
            if mode == 'indirect':
                if vol_name not in ExportedVolumes.vol_names:  # was not yet exported
                    print('Exporting volume, type: "%s", name: "%s"' % (vol_type, vol_name))
                    lux_context.makeNamedVolume(vol_name, vol_type, vol_params)
                    ExportedVolumes.list_exported_volumes(vol_name)  # mark as exported
            else:  # direct
                lux_context.makeNamedVolume(vol_name, vol_type, vol_params)

            return volume_name

        if int_vol_socket.is_linked:
            int_vol_node.export_volume(make_volume=make_volume, make_texture=make_texture)

        if ext_vol_socket.is_linked:
            ext_vol_node.export_volume(make_volume=make_volume, make_texture=make_texture)
        '''

        return set()


@LuxRenderAddon.addon_register_class
class luxrender_volume_output_node(luxrender_node):
    """Volume output node"""
    bl_idname = 'luxrender_volume_output_node'
    bl_label = 'Volume Output'
    bl_icon = 'WORLD'
    bl_width_min = 120

    def init(self, context):
        self.inputs.new('NodeSocketShader', 'Volume')
        self.inputs.new('NodeSocketShader', 'Emission')

    # Todo: export