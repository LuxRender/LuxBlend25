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


@LuxRenderAddon.addon_register_class
class luxrender_mat_node_editor(bpy.types.NodeTree):
    '''LuxRender Material Nodes'''

    bl_idname = 'luxrender_material_nodes'
    bl_label = 'LuxRender Material Nodes'
    bl_icon = 'MATERIAL'

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == 'LUXRENDER_RENDER'
        # This function will set the current node tree to the one belonging
        # to the active material (code orignally from Matt Ebb's 3Delight exporter)

    @classmethod
    def get_from_context(cls, context):
        ob = context.active_object
        if ob and ob.type not in {'LAMP', 'CAMERA'}:
            ma = ob.active_material

            if ma is not None:
                nt_name = ma.luxrender_material.nodetree

                if nt_name:
                    return bpy.data.node_groups[ma.luxrender_material.nodetree], ma, ma
        # Uncomment if/when we make lamp nodes
        # elif ob and ob.type == 'LAMP':
        #     la = ob.data
        #     nt_name = la.luxrender_lamp.nodetree
        #     if nt_name:
        #         return bpy.data.node_groups[la.luxrender_lamp.nodetree], la, la

        return None, None, None

    # This block updates the preview, when socket links change
    def update(self):
        self.refresh = True

    def acknowledge_connection(self, context):
        while self.refresh:
            self.refresh = False
            break

    refresh = bpy.props.BoolProperty(name='Links Changed', default=False, update=acknowledge_connection)


@LuxRenderAddon.addon_register_class
class luxrender_vol_node_editor(bpy.types.NodeTree):
    '''LuxRender Volume Nodes'''

    # The bl_idname is named this way so the volume editor entry comes after the material editor entry in the enum
    bl_idname = 'luxrender_volume_nodes_a'
    bl_label = 'LuxRender Volume Nodes'
    bl_icon = 'MOD_FLUIDSIM'

    @classmethod
    def poll(cls, context):
        return context.scene.render.engine == 'LUXRENDER_RENDER'
        # This function will set the current node tree to the one belonging
        # to the active material (code orignally from Matt Ebb's 3Delight exporter)

    @classmethod
    def get_from_context(cls, context):
        if len(context.scene.luxrender_volumes.volumes) > 0:
            current_vol_ind = context.scene.luxrender_volumes.volumes_index
            current_vol = context.scene.luxrender_volumes.volumes[current_vol_ind]

            if current_vol.nodetree:
                return bpy.data.node_groups[current_vol.nodetree], None, None # TODO context.scene? context.scene.world?

        return None, None, None

    # This block updates the preview, when socket links change
    def update(self):
        self.refresh = True

    def acknowledge_connection(self, context):
        while self.refresh:
            self.refresh = False
            break

    refresh = bpy.props.BoolProperty(name='Links Changed', default=False, update=acknowledge_connection)


# Registered specially in init.py
class luxrender_node_category_material(NodeCategory):
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'luxrender_material_nodes'


luxrender_node_categories_material = [
    # elements that make no sense for materials are disabled or removed

    luxrender_node_category_material("LUX_INPUT", "Input", items=[
        NodeItem("luxrender_2d_coordinates_node"),
        NodeItem("luxrender_3d_coordinates_node"),
        NodeItem("luxrender_texture_constant_node"),  # value node
        NodeItem("luxrender_texture_hitpointcolor_node"),  # vertex color node
        NodeItem("luxrender_texture_hitpointgrey_node"),  # vertex mask node
        NodeItem("luxrender_texture_pointiness_node"),
        NodeItem("luxrender_texture_glossyexponent_node"),
        # NodeItem("NodeGroupInput", poll=group_input_output_item_poll), ...maybe...
    ]),

    luxrender_node_category_material("LUX_MATERIAL", "Material", items=[
        NodeItem("luxrender_material_type_node_standard", label="Standard"),
        NodeItem("luxrender_material_matte_node", label="Matte"),
        NodeItem("luxrender_material_glossy_node", label="Glossy"),
        NodeItem("luxrender_material_mix_node", label="Mix"),
        NodeItem("luxrender_material_null_node", label="Null"),
        NodeItem("luxrender_material_glass_node", label="Glass"),
        NodeItem("luxrender_material_glass2_node", label="Glass2"),
        NodeItem("luxrender_material_roughglass_node", label="Rough Glass"),
        NodeItem("luxrender_material_mattetranslucent_node", label="Matte Translucent"),
        NodeItem("luxrender_material_glossytranslucent_node", label="Glossy Translucent"),
        NodeItem("luxrender_material_metal_node", label="Metal"),
        NodeItem("luxrender_material_metal2_node", label="Metal2"),
        NodeItem("luxrender_material_mirror_node", label="Mirror"),
        NodeItem("luxrender_material_shinymetal_node", label="Shiny Metal"),
        NodeItem("luxrender_material_velvet_node", label="Velvet"),
        NodeItem("luxrender_material_carpaint_node", label="Car Paint"),
        NodeItem("luxrender_material_cloth_node", label="Cloth"),
        NodeItem("luxrender_material_scatter_node", label="Scatter"),
        NodeItem("luxrender_material_glossycoating_node", label="Glossy Coating"),
        NodeItem("luxrender_material_doubleside_node", label="Double-Sided"),
        NodeItem("luxrender_material_layered_node", label="Layered"),
    ]),

    luxrender_node_category_material("LUX_TEXTURE", "Texture", items=[
        NodeItem("luxrender_texture_image_map_node", label="Image Map"),
        NodeItem("luxrender_texture_blender_image_map_node", label="Blender Image Map"),
        NodeItem("luxrender_texture_normal_map_node", label="Normal Map"),
        NodeItem("luxrender_texture_blender_blend_node", label="Blend"),
        NodeItem("luxrender_texture_brick_node", label="Brick"),
        NodeItem("luxrender_texture_blender_clouds_node", label="Clouds"),
        NodeItem("luxrender_texture_vol_cloud_node", label="Cloud"),
        NodeItem("luxrender_texture_blender_distortednoise_node", label="Distorted Noise"),
        NodeItem("luxrender_texture_vol_exponential_node", label="Exponential"),
        NodeItem("luxrender_texture_fbm_node", label="FBM"),
        NodeItem("luxrender_texture_harlequin_node", label="Harlequin"),
        NodeItem("luxrender_texture_blender_marble_node", label="Marble"),
        NodeItem("luxrender_texture_blender_musgrave_node", label="Musgrave"),
        NodeItem("luxrender_texture_blender_stucci_node", label="Stucci"),
        #NodeItem("luxrender_texture_vol_smoke_data_node"),
        NodeItem("luxrender_texture_uv_node", label="UV Test"),
        NodeItem("luxrender_texture_windy_node", label="Windy"),
        NodeItem("luxrender_texture_blender_wood_node", label="Wood"),
        NodeItem("luxrender_texture_wrinkled_node", label="Wrinkled"),
        NodeItem("luxrender_texture_blender_voronoi_node", label="Voronoi"),
    ]),

    luxrender_node_category_material("LUX_CONVERTER", "Converter", items=[
        NodeItem("luxrender_texture_bump_map_node"),
        NodeItem("luxrender_texture_mix_node"),
        NodeItem("luxrender_texture_scale_node"),
        NodeItem("luxrender_texture_add_node"),
        NodeItem("luxrender_texture_subtract_node"),
        NodeItem("luxrender_texture_colorramp_node"),
        #NodeItem("luxrender_texture_colordepth_node"),
    ]),

    luxrender_node_category_material("LUX_FRESNEL", "Fresnel", items=[
        NodeItem("luxrender_texture_fresnelcolor_node"),
        NodeItem("luxrender_texture_fresnelname_node"),
        NodeItem("luxrender_texture_cauchy_node"),
        NodeItem("luxrender_texture_sellmeier_node"),
    ]),

    luxrender_node_category_material("LUX_SPECTRUM", "Spectrum", items=[
        NodeItem("luxrender_texture_blackbody_node"),
        NodeItem("luxrender_texture_gaussian_node"),
        NodeItem("luxrender_texture_tabulateddata_node"),
    ]),

    luxrender_node_category_material("LUX_LIGHT", "Light", items=[
        NodeItem("luxrender_light_area_node"),
    ]),

    luxrender_node_category_material("LUX_OUTPUT", "Output", items=[
        NodeItem("luxrender_material_output_node"),
        # NodeItem("NodeGroupOutput", poll=group_input_output_item_poll),
    ]),

    luxrender_node_category_material("LUX_LAYOUT", "Layout", items=[
        NodeItem("NodeFrame"),
        # NodeItem("NodeReroute") #not working yet
    ]),
]

# Registered specially in init.py
class luxrender_node_category_volume(NodeCategory):
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'luxrender_volume_nodes_a'

luxrender_node_categories_volume = [
    # elements that make no sense for volumes are disabled or removed

    luxrender_node_category_volume("LUX_INPUT_VOLUME", "Input", items=[
        NodeItem("luxrender_2d_coordinates_node"),
        NodeItem("luxrender_3d_coordinates_node"),
        NodeItem("luxrender_texture_constant_node"),  # value node
        #NodeItem("luxrender_texture_glossyexponent_node"),
        #NodeItem("luxrender_texture_hitpointcolor_node"),  # vertex color node
        #NodeItem("luxrender_texture_hitpointgrey_node"),  # vertex mask node
        # NodeItem("NodeGroupInput", poll=group_input_output_item_poll), ...maybe...
    ]),

    luxrender_node_category_volume("LUX_VOLUME", "Volume", items=[
        NodeItem("luxrender_volume_clear_node"),
        NodeItem("luxrender_volume_homogeneous_node"),
        NodeItem("luxrender_volume_heterogeneous_node"),
    ]),

    luxrender_node_category_volume("LUX_TEXTURE_VOLUME", "Texture", items=[
        #NodeItem("luxrender_texture_image_map_node", label="Image Map"),
        #NodeItem("luxrender_texture_blender_image_map_node", label="Blender Image Map"),
        #NodeItem("luxrender_texture_normal_map_node", label="Normal Map"),
        NodeItem("luxrender_texture_blender_blend_node", label="Blend"),
        NodeItem("luxrender_texture_brick_node", label="Brick"),
        NodeItem("luxrender_texture_blender_clouds_node", label="Clouds"),
        NodeItem("luxrender_texture_vol_cloud_node", label="Cloud"),
        NodeItem("luxrender_texture_blender_distortednoise_node", label="Distorted Noise"),
        NodeItem("luxrender_texture_vol_exponential_node", label="Exponential"),
        NodeItem("luxrender_texture_fbm_node", label="FBM"),
        #NodeItem("luxrender_texture_harlequin_node", label="Harlequin"),
        NodeItem("luxrender_texture_blender_marble_node", label="Marble"),
        NodeItem("luxrender_texture_blender_musgrave_node", label="Musgrave"),
        NodeItem("luxrender_texture_blender_stucci_node", label="Stucci"),
        NodeItem("luxrender_texture_vol_smoke_data_node", label="Smoke Data"),
        #NodeItem("luxrender_texture_uv_node", label="UV Test"),
        NodeItem("luxrender_texture_windy_node", label="Windy"),
        NodeItem("luxrender_texture_blender_wood_node", label="Wood"),
        NodeItem("luxrender_texture_wrinkled_node", label="Wrinkled"),
        NodeItem("luxrender_texture_blender_voronoi_node", label="Voronoi"),
    ]),

    luxrender_node_category_volume("LUX_CONVERTER_VOLUME", "Converter", items=[
        NodeItem("luxrender_texture_colordepth_node"),
        NodeItem("luxrender_texture_mix_node"),
        NodeItem("luxrender_texture_scale_node"),
        NodeItem("luxrender_texture_add_node"),
        NodeItem("luxrender_texture_subtract_node"),
        NodeItem("luxrender_texture_colorramp_node"),
        #NodeItem("luxrender_texture_bump_map_node"),
    ]),

    luxrender_node_category_volume("LUX_FRESNEL_VOLUME", "Fresnel", items=[
        NodeItem("luxrender_texture_fresnelcolor_node"),
        NodeItem("luxrender_texture_fresnelname_node"),
        NodeItem("luxrender_texture_cauchy_node"),
        NodeItem("luxrender_texture_sellmeier_node"),
    ]),

    luxrender_node_category_volume("LUX_SPECTRUM_VOLUME", "Spectrum", items=[
        NodeItem("luxrender_texture_blackbody_node"),
        NodeItem("luxrender_texture_gaussian_node"),
        NodeItem("luxrender_texture_tabulateddata_node"),
    ]),

    luxrender_node_category_volume("LUX_LIGHT_VOLUME", "Light", items=[
        NodeItem("luxrender_light_area_node"),
    ]),

    luxrender_node_category_volume("LUX_OUTPUT_VOLUME", "Output", items=[
        NodeItem("luxrender_volume_output_node"),
        # NodeItem("NodeGroupOutput", poll=group_input_output_item_poll),
    ]),

    luxrender_node_category_volume("LUX_LAYOUT_VOLUME", "Layout", items=[
        NodeItem("NodeFrame"),
        # NodeItem("NodeReroute") #not working yet
    ]),
]