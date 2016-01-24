# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 LuxRender Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Doug Hammond, Simon Wendsche (BYOB)
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
#
import bpy, bl_ui

from ..extensions_framework.ui import property_group_renderer

from ..outputs.luxcore_api import UseLuxCore, pyluxcore
from .. import LuxRenderAddon


class imageeditor_panel(property_group_renderer):
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    COMPAT_ENGINES = 'LUXRENDER_RENDER'

    @classmethod
    def poll(cls, context):
        engine_is_lux = context.scene.render.engine in cls.COMPAT_ENGINES
        return engine_is_lux and UseLuxCore()


@LuxRenderAddon.addon_register_class
class rendering_controls_panel(imageeditor_panel):
    bl_label = 'LuxRender Controls'
    COMPAT_ENGINES = 'LUXRENDER_RENDER'

    def draw(self, context):
        if context.scene.luxcore_rendering_controls.pause_render:
            button_text = 'Resume Render'
            button_icon = 'PLAY'
        else:
            button_text = 'Pause Render'
            button_icon = 'PAUSE'

        self.layout.prop(context.scene.luxcore_rendering_controls, 'pause_render', toggle=True, text=button_text,
                         icon=button_icon)


@LuxRenderAddon.addon_register_class
class tonemapping_panel(imageeditor_panel):
    bl_label = 'LuxRender Imagepipeline'
    COMPAT_ENGINES = 'LUXRENDER_RENDER'

    def draw(self, context):
        if not hasattr(pyluxcore.RenderSession, 'Parse'):
            self.layout.label('Outdated LuxCore version!', icon='INFO')
            return

        if context.scene.camera is None:
            self.layout.label('No camera in scene.')
            return

        lux_cam = context.scene.camera.data.luxrender_camera
        imagepipeline_settings = lux_cam.luxcore_imagepipeline_settings

        self.layout.prop(imagepipeline_settings, 'displayinterval')

        self.layout.label('Tonemapper:')
        self.layout.prop(imagepipeline_settings, 'tonemapper_type')

        if imagepipeline_settings.tonemapper_type in ['TONEMAP_LINEAR', 'TONEMAP_LUXLINEAR']:
            self.layout.prop(imagepipeline_settings, 'use_auto_linear')

        if imagepipeline_settings.tonemapper_type == 'TONEMAP_LINEAR':
            self.layout.prop(imagepipeline_settings, 'linear_scale')
        elif imagepipeline_settings.tonemapper_type == 'TONEMAP_LUXLINEAR':
            # Since fstop and exposure time should also change DOF/motion blur we don't show them here - ISO is enough
            self.layout.prop(lux_cam, 'sensitivity')
        elif imagepipeline_settings.tonemapper_type == 'TONEMAP_REINHARD02':
            sub = self.layout.column(align=True)
            sub.prop(imagepipeline_settings, 'reinhard_prescale')
            sub.prop(imagepipeline_settings, 'reinhard_postscale')
            sub.prop(imagepipeline_settings, 'reinhard_burn')

        self.layout.prop(imagepipeline_settings, 'use_bloom')
        if imagepipeline_settings.use_bloom:
            col = self.layout.column(align=True)
            col.prop(imagepipeline_settings, 'bloom_radius')
            col.prop(imagepipeline_settings, 'bloom_weight')

        self.layout.label('Analog Film Simulation:')
        self.layout.prop(imagepipeline_settings, 'crf_type', expand=True)
        if imagepipeline_settings.crf_type == 'PRESET':
            self.layout.menu('IMAGEPIPELINE_MT_luxrender_crf', text=imagepipeline_settings.crf_preset)
        elif imagepipeline_settings.crf_type == 'FILE':
            self.layout.prop(imagepipeline_settings, 'crf_file')

        # TODO: can we only show the available passes here?
        self.layout.label('Pass:')
        self.layout.prop(imagepipeline_settings, 'output_switcher_pass')

        if imagepipeline_settings.output_switcher_pass == 'IRRADIANCE':
            sub = self.layout.column(align=True)
            row = sub.row(align=True)
            row.prop(imagepipeline_settings, 'contour_scale')
            row.prop(imagepipeline_settings, 'contour_range')
            row = sub.row(align=True)
            row.prop(imagepipeline_settings, 'contour_steps')
            row.prop(imagepipeline_settings, 'contour_zeroGridSize')


@LuxRenderAddon.addon_register_class
class halt_conditions_panel(imageeditor_panel):
    bl_label = 'LuxRender Halt Conditions'
    COMPAT_ENGINES = 'LUXRENDER_RENDER'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.luxcore_enginesettings

        def draw_condition_pair(halt_conditon):
            """
            designed for halt conditons of the form 'use_<name>' and '<name>', where the first is the checkbox and
            the second is the value (e.g. 'use_halt_samples' is a boolean and 'halt_samples' is an int)
            """
            bool_name = 'use_%s' % halt_conditon

            row = layout.row()
            row.prop(settings, bool_name)
            sub = row.split()
            sub.active = getattr(settings, bool_name)
            sub.prop(settings, halt_conditon)

        if settings.renderengine_type == 'BIASPATH':
            layout.prop(settings, 'tile_multipass_enable')

            column = layout.column()
            column.enabled = settings.tile_multipass_enable

            column.prop(settings, 'tile_multipass_convergencetest_threshold')
            column.prop(settings, 'tile_multipass_use_threshold_reduction')

            sub_column = column.split()
            sub_column.enabled = settings.tile_multipass_use_threshold_reduction
            sub_column.prop(settings, 'tile_multipass_convergencetest_threshold_reduction')
        else:
            draw_condition_pair('halt_samples')
            draw_condition_pair('halt_time')
            draw_condition_pair('halt_noise')


@LuxRenderAddon.addon_register_class
class rendering_statistics_panel(imageeditor_panel):
    bl_label = 'LuxRender Statistics'
    COMPAT_ENGINES = 'LUXRENDER_RENDER'

    def draw(self, context):
        box = self.layout.box()
        for elem in context.scene.luxcore_rendering_controls.controls:
            box.prop(context.scene.luxcore_rendering_controls, elem)

        if bpy.context.scene.luxcore_enginesettings.renderengine_type == 'BIASPATH':
            box = self.layout.box()
            box.prop(context.scene.luxcore_tile_highlighting, 'use_tile_highlighting')

            if context.scene.luxcore_tile_highlighting.use_tile_highlighting:
                box.separator()
                box.prop(context.scene.luxcore_tile_highlighting, 'show_converged')
                box.prop(context.scene.luxcore_tile_highlighting, 'show_unconverged')
                box.prop(context.scene.luxcore_tile_highlighting, 'show_pending')