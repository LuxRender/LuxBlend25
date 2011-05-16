# -*- coding: utf8 -*-
#
# ***** BEGIN GPL LICENSE BLOCK *****
#
# --------------------------------------------------------------------------
# Blender 2.5 LuxRender Add-On
# --------------------------------------------------------------------------
#
# Authors:
# Doug Hammond
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
from extensions_framework import declarative_property_group
from extensions_framework.validate import Logic_OR as O, Logic_Operator as LO

from .. import LuxRenderAddon
from ..export import ParamSet
from ..outputs import LuxLog
from ..outputs.pure_api import LUXRENDER_VERSION

def volumeintegrator_types():
	items = [
		('emission', 'Emission', 'emission'),
		('single', 'Single', 'single'),
	]
	
	if LUXRENDER_VERSION >= '0.8':
		items.append(
			('multi', 'Multi', 'multi'),
		)
		
	return items

@LuxRenderAddon.addon_register_class
class luxrender_volumeintegrator(declarative_property_group):
	'''
	Storage class for LuxRender Volume Integrator settings.
	'''
	
	ef_attach_to = ['Scene']
	
	controls = [
		'volumeintegrator', 'stepsize'
	]
	
	properties = [
		{
			'type': 'enum',
			'attr': 'volumeintegrator',
			'name': 'Volume Integrator',
			'description': 'Volume Integrator',
			'default': 'single' if LUXRENDER_VERSION < '0.8' else 'multi',
			'items': volumeintegrator_types(),
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'stepsize',
			'name': 'Step Size',
			'description': 'Volume Integrator Step Size',
			'default': 1.0,
			'min': 0.0,
			'soft_min': 0.0,
			'max': 100.0,
			'soft_max': 100.0,
			'save_in_preset': True
		}
	]
	
	def api_output(self):
		'''
		Format this class's members into a LuxRender ParamSet
		
		Returns dict
		'''
		
		params = ParamSet()
		
		params.add_float('stepsize', self.stepsize)
		
		return self.volumeintegrator, params

@LuxRenderAddon.addon_register_class
class luxrender_integrator(declarative_property_group):
	'''
	Storage class for LuxRender SurfaceIntegrator settings.
	'''
	
	ef_attach_to = ['Scene']
	
	controls = [
		[ 0.7, 'surfaceintegrator', 'advanced'],
		
		'lightstrategy',
		
		# bidir +
		['eyedepth', 'lightdepth'],
		['eyerrthreshold', 'lightrrthreshold'],
		
		# dl +
		'maxdepth',
		
		# dp
		['lbl_direct',
		'directsamples'],
		['directsampleall',
		'directdiffuse',
		'directglossy'],
		['lbl_indirect',
		'indirectsamples'],
		['indirectsampleall',
		'indirectdiffuse',
		'indirectglossy'],
		'lbl_diffuse',
		['diffusereflectsamples',
		'diffusereflectdepth'],
		['diffuserefractsamples',
		'diffuserefractdepth'],
		'lbl_glossy',
		['glossyreflectsamples',
		'glossyreflectdepth'],
		['glossyrefractsamples',
		'glossyrefractdepth'],
		'lbl_specular',
		['specularreflectdepth',
		'specularrefractdepth'],
		'lbl_rejection',
		['diffusereflectreject',
		'diffusereflectreject_threshold'],
		['diffuserefractreject',
		'diffuserefractreject_threshold'],
		['glossyreflectreject',
		'glossyreflectreject_threshold'],
		['glossyrefractreject',
		'glossyrefractreject_threshold'],
		
		# epm
		'maxphotondepth',
		'directphotons',
		'causticphotons',
		'indirectphotons',
		'radiancephotons',
		'nphotonsused',
		'maxphotondist',
		'finalgather',
		'finalgathersamples',
		'gatherangle',
		'renderingmode',
		'rrstrategy',
		'rrcontinueprob',
		# epm advanced
		'distancethreshold',
		'photonmapsfile',
		'dbg_enabledirect',
		'dbg_enableradiancemap',
		'dbg_enableindircaustic',
		'dbg_enableindirdiffuse',
		'dbg_enableindirspecular',
		
		# igi
		'nsets',
		'nlights',
		'mindist',
		
		#sppm
		'maxeyedepth',
		'photonperpass',
		'startradius',
		'alpha',
		'lookupaccel',
		'pixelsampler',
				
		# path
		'includeenvironment',
	]
	
	visibility = {
		# bidir +
		'eyedepth':							{ 'surfaceintegrator': 'bidirectional' },
		'lightdepth':						{ 'surfaceintegrator': 'bidirectional' },
		'eyerrthreshold':					{ 'advanced': True, 'surfaceintegrator': 'bidirectional' },
		'lightrrthreshold':					{ 'advanced': True, 'surfaceintegrator': 'bidirectional' },
		
		# dl +
		'lightstrategy':					{ 'advanced': True, 'surfaceintegrator': O(['directlighting', 'exphotonmap', 'igi', 'path',  'distributedpath'])},
		'maxdepth':							{ 'surfaceintegrator': O(['directlighting', 'exphotonmap', 'igi', 'path']) },
		
		# dp
		'lbl_direct':						{ 'surfaceintegrator': 'distributedpath' },
		'directsampleall':					{ 'surfaceintegrator': 'distributedpath' },
		'directsamples':					{ 'surfaceintegrator': 'distributedpath' },
		'directdiffuse':					{ 'surfaceintegrator': 'distributedpath' },
		'directglossy':						{ 'surfaceintegrator': 'distributedpath' },
		'lbl_indirect':						{ 'surfaceintegrator': 'distributedpath' },
		'indirectsampleall':				{ 'surfaceintegrator': 'distributedpath' },
		'indirectsamples':					{ 'surfaceintegrator': 'distributedpath' },
		'indirectdiffuse':					{ 'surfaceintegrator': 'distributedpath' },
		'indirectglossy':					{ 'surfaceintegrator': 'distributedpath' },
		'lbl_diffuse':						{ 'surfaceintegrator': 'distributedpath' },
		'diffusereflectdepth':				{ 'surfaceintegrator': 'distributedpath' },
		'diffusereflectsamples':			{ 'surfaceintegrator': 'distributedpath' },
		'diffuserefractdepth':				{ 'surfaceintegrator': 'distributedpath' },
		'diffuserefractsamples':			{ 'surfaceintegrator': 'distributedpath' },
		'lbl_glossy':						{ 'surfaceintegrator': 'distributedpath' },
		'glossyreflectdepth':				{ 'surfaceintegrator': 'distributedpath' },
		'glossyreflectsamples':				{ 'surfaceintegrator': 'distributedpath' },
		'glossyrefractdepth':				{ 'surfaceintegrator': 'distributedpath' },
		'glossyrefractsamples':				{ 'surfaceintegrator': 'distributedpath' },
		'lbl_specular':						{ 'surfaceintegrator': 'distributedpath' },
		'specularreflectdepth':				{ 'surfaceintegrator': 'distributedpath' },
		'specularrefractdepth':				{ 'surfaceintegrator': 'distributedpath' },
		'lbl_rejection':					{ 'surfaceintegrator': 'distributedpath' },
		'diffusereflectreject':				{ 'surfaceintegrator': 'distributedpath' },
		'diffusereflectreject_threshold':	{ 'diffusereflectreject': True, 'surfaceintegrator': 'distributedpath' },
		'diffuserefractreject':				{ 'surfaceintegrator': 'distributedpath' },
		'diffuserefractreject_threshold':	{ 'diffuserefractreject': True, 'surfaceintegrator': 'distributedpath' },
		'glossyreflectreject':				{ 'surfaceintegrator': 'distributedpath' },
		'glossyreflectreject_threshold':	{ 'glossyreflectreject': True, 'surfaceintegrator': 'distributedpath' },
		'glossyrefractreject':				{ 'surfaceintegrator': 'distributedpath' },
		'glossyrefractreject_threshold':	{ 'glossyrefractreject': True, 'surfaceintegrator': 'distributedpath' },
		
		# epm
		'maxphotondepth':					{ 'surfaceintegrator': O(['exphotonmap', 'sppm']) },
		'directphotons':					{ 'surfaceintegrator': 'exphotonmap' },
		'causticphotons':					{ 'surfaceintegrator': 'exphotonmap' },
		'indirectphotons':					{ 'surfaceintegrator': 'exphotonmap' },
		'radiancephotons':					{ 'surfaceintegrator': 'exphotonmap' },
		'nphotonsused':						{ 'surfaceintegrator': 'exphotonmap' },
		'maxphotondist':					{ 'surfaceintegrator': 'exphotonmap' },
		'finalgather':						{ 'surfaceintegrator': 'exphotonmap' },
		'finalgathersamples':				{ 'finalgather': True, 'surfaceintegrator': 'exphotonmap' },
		'gatherangle':						{ 'finalgather': True, 'surfaceintegrator': 'exphotonmap' },
		'renderingmode':					{ 'surfaceintegrator': 'exphotonmap' },
		'rrstrategy':						{ 'surfaceintegrator': O(['exphotonmap', 'path']) },
		'rrcontinueprob':					{ 'surfaceintegrator': O(['exphotonmap', 'path']) },
		# epm advanced
		'distancethreshold':				{ 'advanced': True, 'surfaceintegrator': 'exphotonmap' },
		'photonmapsfile':					{ 'advanced': True, 'surfaceintegrator': 'exphotonmap' },
		'dbg_enabledirect':					{ 'advanced': True, 'surfaceintegrator': 'exphotonmap' },
		'dbg_enableradiancemap':			{ 'advanced': True, 'surfaceintegrator': 'exphotonmap' },
		'dbg_enableindircaustic':			{ 'advanced': True, 'surfaceintegrator': 'exphotonmap' },
		'dbg_enableindirdiffuse':			{ 'advanced': True, 'surfaceintegrator': 'exphotonmap' },
		'dbg_enableindirspecular':			{ 'advanced': True, 'surfaceintegrator': 'exphotonmap' },
		
		# igi
		'nsets':							{ 'surfaceintegrator': 'igi' },
		'nlights':							{ 'surfaceintegrator': 'igi' },
		'mindist':							{ 'surfaceintegrator': 'igi' },
		
		# path
		'includeenvironment':				{ 'surfaceintegrator': O(['sppm', 'path']) },
		
		# sppm
		'maxeyedepth':						{ 'surfaceintegrator': 'sppm' },
		'photonperpass':					{ 'surfaceintegrator': 'sppm' },
		'startradius':						{ 'surfaceintegrator': 'sppm' },

		# sppm advanced
		'alpha':							{ 'advanced': True, 'surfaceintegrator': 'sppm' },
		'lookupaccel':						{ 'advanced': True, 'surfaceintegrator': 'sppm' },
		'pixelsampler':						{ 'advanced': True, 'surfaceintegrator': 'sppm' },
	}
	
	properties = [
		{
			'type': 'enum', 
			'attr': 'surfaceintegrator',
			'name': 'Surface Integrator',
			'description': 'Surface Integrator',
			'default': 'bidirectional',
			'items': [
				('bidirectional', 'Bi-Directional', 'bidirectional'),
				('path', 'Path', 'path'),
				('directlighting', 'Direct Lighting', 'directlighting'),
				('distributedpath', 'Distributed Path', 'distributedpath'),
				('igi', 'Instant Global Illumination', 'igi',),
				('exphotonmap', 'Ex-Photon Map', 'exphotonmap'),
				('sppm', 'SPPM', 'sppm'),
			],
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'advanced',
			'name': 'Advanced',
			'description': 'Configure advanced integrator settings',
			'default': False,
			'save_in_preset': True
		},
		{
			'type': 'enum',
			'attr': 'lightstrategy',
			'name': 'Light Strategy',
			'description': 'Light Sampling Strategy',
			'default': 'auto',
			'items': [
				('auto', 'Auto', 'auto'),
				('one', 'One', 'one'),
				('all', 'All', 'all'),
				('importance', 'Importance', 'importance'),
				('powerimp', 'Power', 'powerimp'),
				('allpowerimp', 'All Power', 'allpowerimp'),
				('logpowerimp', 'Log Power', 'logpowerimp')
			],
			'save_in_preset': True
		},
		{
			'type': 'int', 
			'attr': 'eyedepth',
			'name': 'Eye Depth',
			'description': 'Max recursion depth for ray casting from eye',
			'default': 48,
			'min': 0,
			'max': 2048,
			'save_in_preset': True
		},
		{
			'type': 'int', 
			'attr': 'lightdepth',
			'name': 'Light Depth',
			'description': 'Max recursion depth for ray casting from light',
			'default': 48,
			'min': 0,
			'max': 2048,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'eyerrthreshold',
			'name': 'Eye RR Threshold',
			'default': 0.0,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'lightrrthreshold',
			'name': 'Light RR Threshold',
			'default': 0.0,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'maxdepth',
			'name': 'Max. depth',
			'default': 48,
			'save_in_preset': True
		},
		
		{
			'type': 'text',
			'attr': 'lbl_direct',
			'name': 'Direct light sampling',
		},
		{
			'type': 'bool',
			'attr': 'directsampleall',
			'name': 'Sample all',
			'default': True,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'directsamples',
			'name': 'Samples',
			'default': 1,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'directdiffuse',
			'name': 'Diffuse',
			'default': True,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'directglossy',
			'name': 'Glossy',
			'default': True,
			'save_in_preset': True
		},
		
		{
			'type': 'text',
			'attr': 'lbl_indirect',
			'name': 'Indirect light sampling',
		},
		{
			'type': 'bool',
			'attr': 'indirectsampleall',
			'name': 'Sample all',
			'default': False,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'indirectsamples',
			'name': 'Samples',
			'default': 1,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'indirectdiffuse',
			'name': 'Diffuse',
			'default': True,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'indirectglossy',
			'name': 'Glossy',
			'default': True,
			'save_in_preset': True
		},
		
		{
			'type': 'text',
			'attr': 'lbl_diffuse',
			'name': 'Diffuse settings',
		},
		{
			'type': 'int',
			'attr': 'diffusereflectdepth',
			'name': 'Reflection depth',
			'default': 3,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'diffusereflectsamples',
			'name': 'Reflection samples',
			'default': 1,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'diffuserefractdepth',
			'name': 'Refraction depth',
			'default': 5,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'diffuserefractsamples',
			'name': 'Refraction samples',
			'default': 1,
			'save_in_preset': True
		},
		
		{
			'type': 'text',
			'attr': 'lbl_glossy',
			'name': 'Glossy settings',
		},
		{
			'type': 'int',
			'attr': 'glossyreflectdepth',
			'name': 'Reflection depth',
			'default': 2,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'glossyreflectsamples',
			'name': 'Reflection samples',
			'default': 1,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'glossyrefractdepth',
			'name': 'Refraction depth',
			'default': 5,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'glossyrefractsamples',
			'name': 'Refraction samples',
			'default': 1,
			'save_in_preset': True
		},
		
		{
			'type': 'text',
			'attr': 'lbl_specular',
			'name': 'Specular settings',
		},
		{
			'type': 'int',
			'attr': 'specularreflectdepth',
			'name': 'Reflection depth',
			'default': 3,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'specularrefractdepth',
			'name': 'Refraction depth',
			'default': 5,
			'save_in_preset': True
		},
		
		{
			'type': 'text',
			'attr': 'lbl_rejection',
			'name': 'Rejection settings',
		},
		{
			'type': 'bool',
			'attr': 'diffusereflectreject',
			'name': 'Diffuse reflection reject',
			'default': False,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'diffusereflectreject_threshold',
			'name': 'Threshold',
			'default': 10.0,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'diffuserefractreject',
			'name': 'Diffuse refraction reject',
			'default': False,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'diffuserefractreject_threshold',
			'name': 'Threshold',
			'default': 10.0,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'glossyreflectreject',
			'name': 'Glossy reflection reject',
			'default': False,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'glossyreflectreject_threshold',
			'name': 'Threshold',
			'default': 10.0,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'glossyrefractreject',
			'name': 'Glossy refraction reject',
			'default': False,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'glossyrefractreject_threshold',
			'name': 'Threshold',
			'default': 10.0,
			'save_in_preset': True
		},
		
		{
			'type': 'int',
			'attr': 'maxphotondepth',
			'name': 'Max. photon depth',
			'default': 16,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'directphotons',
			'name': 'Direct photons',
			'default': 1000000,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'causticphotons',
			'name': 'Caustic photons',
			'default': 20000,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'indirectphotons',
			'name': 'Indirect photons',
			'default': 200000,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'radiancephotons',
			'name': 'Radiance photons',
			'default': 200000,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'nphotonsused',
			'name': 'Number of photons used',
			'default': 50,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'maxphotondist',
			'name': 'Max. photon distance',
			'default': 0.1,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'finalgather',
			'name': 'Final Gather',
			'default': True,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'finalgathersamples',
			'name': 'Final gather samples',
			'default': 32,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'gatherangle',
			'name': 'Gather angle',
			'default': 10.0,
			'save_in_preset': True
		},
		{
			'type': 'enum',
			'attr': 'renderingmode',
			'name': 'Rendering mode',
			'default': 'directlighting',
			'items': [
				('directlighting', 'Direct Lighting', 'directlighting'),
				('path', 'Path', 'path'),
			],
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'distancethreshold',
			'name': 'Distance threshold',
			'default': 0.75,
			'save_in_preset': True
		},
		{
			'type': 'string',
			'subtype': 'FILE_PATH',
			'attr': 'photonmapsfile',
			'name': 'Photonmaps file',
			'default': '',
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'dbg_enabledirect',
			'name': 'Debug: Enable direct',
			'default': True,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'dbg_enableradiancemap',
			'name': 'Debug: Enable radiance map',
			'default': False,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'dbg_enableindircaustic',
			'name': 'Debug: Enable indirect caustics',
			'default': True,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'dbg_enableindirdiffuse',
			'name': 'Debug: Enable indirect diffuse',
			'default': True,
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'dbg_enableindirspecular',
			'name': 'Debug: Enable indirect specular',
			'default': True,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'nsets',
			'name': 'Number of sets',
			'default': 4,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'nlights',
			'name': 'Number of lights',
			'default': 64,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'mindist',
			'name': 'Min. Distance',
			'default': 0.1,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'rrcontinueprob',
			'name': 'RR continue probability',
			'default': 0.65,
			'save_in_preset': True
		},
		{
			'type': 'enum',
			'attr': 'rrstrategy',
			'name': 'RR strategy',
			'default': 'efficiency',
			'items': [
				('efficiency', 'efficiency', 'efficiency'),
				('probability', 'probability', 'probability'),
				('none', 'none', 'none'),
			],
			'save_in_preset': True
		},
		{
			'type': 'bool',
			'attr': 'includeenvironment',
			'name': 'Include Environment',
			'default': True,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'maxeyedepth',
			'name': 'Max. eye depth',
			'default': 16,
			'save_in_preset': True
		},
		{
			'type': 'int',
			'attr': 'photonperpass',
			'name': 'Photons per pass',
			'default': 1000000,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'startradius',
			'name': 'Starting radius',
			'default': 2.0,
			'save_in_preset': True
		},
		{
			'type': 'float',
			'attr': 'alpha',
			'name': 'Alpha',
			'default': 0.7,
			'min': 0.01,
			'max': 0.99,
			'save_in_preset': True
		},
		{
			'type': 'enum',
			'attr': 'lookupaccel',
			'name': 'Lookup accelerator',
			'default': 'hybridhashgrid',
			'items': [
				('hashgrid', 'Hash Grid', 'hashgrid'),
				('kdtree', 'KD Tree', 'kdtree'),
				('hybridhashgrid', 'Hybrid Hash Grid', 'hybridhashgrid'),
	#			('stochastichashgrid', 'Stochastic Hash Grid', 'stochastichashgrid'),
				('grid', 'Grid', 'grid'),
	#			('cuckoohashgrid', 'Cuckoo Hash Grid', 'cuckoohashgrid'),
				('hybridmultihashgrid', 'Hybrid Multihash Grid', 'hybridmultihashgrid'),
	#			('stochasticmultihashgrid', 'Stochastic Multihash Grid', 'stochasticmultihashgrid'),
	# Some of these are works-in-progress in the core, so are commented out for now.
			],
			'save_in_preset': True
		},
		{
			'type': 'enum',
			'attr': 'pixelsampler',
			'name': 'Pixel sampler',
			'default': 'vegas',
			'description': 'Sampling pattern used during the eye pass',
			'items': [
				('vegas', 'Vegas', 'vegas'),
				('linear', 'Linear', 'linear'),
				('tile', 'Tile', 'tile'),
				('hilbert', 'Hilbert', 'hilbert'),
			],
			'save_in_preset': True
		},
	]
	
	def api_output(self, engine_properties):
		'''
		Format this class's members into a LuxRender ParamSet
		
		Returns tuple
		'''
		
		params = ParamSet()
		
		if engine_properties.renderer == 'hybrid':
			if self.surfaceintegrator != 'path':
				LuxLog('Incompatible surface integrator for Hybrid renderer (use "path").')
				raise Exception('Incompatible render settings')
			if self.lightstrategy != 'one':
				LuxLog('Incompatible lightstrategy for Hybrid renderer (use "one").')
				raise Exception('Incompatible render settings')
				
		#SPPM requires that renderer and engine both = sppm, neither option works without the other. Here we ensure that the user set both.
		if engine_properties.renderer == 'sppm':
			if self.surfaceintegrator != 'sppm':
				LuxLog('SPPM Renderer requires SPPM surface integrator.')
				raise Exception('Incompatible render settings')
				
		if self.surfaceintegrator == 'sppm':
			if engine_properties.renderer != 'sppm':
				LuxLog('SPPM surface integrator only works with SPPM renderer, select it under "Renderer" in LuxRender Engine Configuration.')
				raise Exception('Incompatible render settings')
		
		if self.surfaceintegrator == 'bidirectional':
			params.add_integer('eyedepth', self.eyedepth) \
				  .add_integer('lightdepth', self.lightdepth)
			if self.advanced:
				params.add_float('eyerrthreshold', self.eyerrthreshold)
				params.add_float('lightrrthreshold', self.lightrrthreshold)
		
		if self.surfaceintegrator == 'directlighting':
			params.add_integer('maxdepth', self.maxdepth)
			
		if self.surfaceintegrator == 'sppm':
			params.add_integer('maxeyedepth', self.maxeyedepth) \
				  .add_integer('maxphotondepth', self.maxphotondepth) \
				  .add_integer('photonperpass', self.photonperpass) \
				  .add_float('startradius', self.startradius) \
				  .add_bool('includeenvironment', self.includeenvironment)
			if self.advanced:
				params.add_float('alpha', self.alpha) \
				  .add_string('lookupaccel', self.lookupaccel) \
				  .add_string('pixelsampler', self.pixelsampler)
		
		if self.surfaceintegrator == 'distributedpath':
			params.add_bool('directsampleall', self.directsampleall) \
				  .add_integer('directsamples', self.directsamples) \
				  .add_bool('directdiffuse', self.directdiffuse) \
				  .add_bool('directglossy', self.directglossy) \
				  .add_bool('indirectsampleall', self.indirectsampleall) \
				  .add_integer('indirectsamples', self.indirectsamples) \
				  .add_bool('indirectdiffuse', self.indirectdiffuse) \
				  .add_bool('indirectglossy', self.indirectglossy) \
				  .add_integer('diffusereflectdepth', self.diffusereflectdepth) \
				  .add_integer('diffusereflectsamples', self.diffusereflectsamples) \
				  .add_integer('diffuserefractdepth', self.diffuserefractdepth) \
				  .add_integer('diffuserefractsamples', self.diffuserefractsamples) \
				  .add_integer('glossyreflectdepth', self.glossyreflectdepth) \
				  .add_integer('glossyreflectsamples', self.glossyreflectsamples) \
				  .add_integer('glossyrefractdepth', self.glossyrefractdepth) \
				  .add_integer('glossyrefractsamples', self.glossyrefractsamples) \
				  .add_integer('specularreflectdepth', self.specularreflectdepth) \
				  .add_integer('specularrefractdepth', self.specularrefractdepth) \
				  .add_bool('diffusereflectreject', self.diffusereflectreject) \
				  .add_float('diffusereflectreject_threshold', self.diffusereflectreject_threshold) \
				  .add_bool('diffuserefractreject', self.diffuserefractreject) \
				  .add_float('diffuserefractreject_threshold', self.diffuserefractreject_threshold) \
				  .add_bool('glossyreflectreject', self.glossyreflectreject) \
				  .add_float('glossyreflectreject_threshold', self.glossyreflectreject_threshold) \
				  .add_bool('glossyrefractreject', self.glossyrefractreject) \
				  .add_float('glossyrefractreject_threshold', self.glossyrefractreject_threshold)
		
		if self.surfaceintegrator == 'exphotonmap':
			params.add_integer('maxdepth', self.maxdepth) \
				  .add_integer('maxphotondepth', self.maxphotondepth) \
				  .add_integer('directphotons', self.directphotons) \
				  .add_integer('causticphotons', self.causticphotons) \
				  .add_integer('indirectphotons', self.indirectphotons) \
				  .add_integer('radiancephotons', self.radiancephotons) \
				  .add_integer('nphotonsused', self.nphotonsused) \
				  .add_float('maxphotondist', self.maxphotondist) \
				  .add_bool('finalgather', self.finalgather) \
				  .add_integer('finalgathersamples', self.finalgathersamples) \
				  .add_string('renderingmode', self.renderingmode) \
				  .add_float('gatherangle', self.gatherangle) \
				  .add_string('rrstrategy', self.rrstrategy) \
				  .add_float('rrcontinueprob', self.rrcontinueprob)
			if self.advanced:
				params.add_float('distancethreshold', self.distancethreshold) \
					  .add_string('photonmapsfile', self.photonmapsfile) \
					  .add_bool('dbg_enabledirect', self.dbg_enabledirect) \
					  .add_bool('dbg_enableradiancemap', self.dbg_enableradiancemap) \
					  .add_bool('dbg_enableindircaustic', self.dbg_enableindircaustic) \
					  .add_bool('dbg_enableindirdiffuse', self.dbg_enableindirdiffuse) \
					  .add_bool('dbg_enableindirspecular', self.dbg_enableindirspecular)
		
		if self.surfaceintegrator == 'igi':
			params.add_integer('nsets', self.nsets) \
				  .add_integer('nlights', self.nlights) \
				  .add_integer('maxdepth', self.maxdepth) \
				  .add_float('mindist', self.mindist)
		
		if self.surfaceintegrator == 'path':
			params.add_integer('maxdepth', self.maxdepth) \
				  .add_float('rrcontinueprob', self.rrcontinueprob) \
				  .add_string('rrstrategy', self.rrstrategy) \
				  .add_bool('includeenvironment', self.includeenvironment)
		
		if self.advanced and self.surfaceintegrator not in ('bidirectional', 'sppm'):
			params.add_string('lightstrategy', self.lightstrategy)
		
		return self.surfaceintegrator, params
