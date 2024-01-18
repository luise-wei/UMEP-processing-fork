# -*- coding: utf-8 -*-

"""
/***************************************************************************
 ProcessingUMEP
                                 A QGIS plugin
 UMEP for processing toolbox
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2020-04-02
        copyright            : (C) 2020 by Fredrik Lindberg
        email                : fredrikl@gvc.gu.se
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

__author__ = 'Fredrik Lindberg'
__date__ = '2020-04-02'
__copyright__ = '(C) 2020 by Fredrik Lindberg'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from osgeo import gdal
from osgeo.gdalconst import *
import numpy as np
import os
from functions import wallalgorithms as wa
import inspect
from pathlib import Path
from util.misc import saverasternd
import errno
from types import SimpleNamespace
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)
FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
# logging.basicConfig(format=FORMAT)
logger.setLevel(logging.WARNING)
logger.propagate = False

class DummyFeedback(SimpleNamespace):
    """class to mock QgsFeedback class in standalone algorithms"""

    def isCanceled(self):
        return False

    def setProgress(self, value: int):
        return

# def saverasternd(gdal_data, filename, raster):
#     rows = gdal_data.RasterYSize
#     cols = gdal_data.RasterXSize

#     outDs = gdal.GetDriverByName("GTiff").Create(filename, cols, rows, int(1), GDT_Float32)
#     outBand = outDs.GetRasterBand(1)

#     # write the data
#     outBand.WriteArray(raster, 0, 0)
#     # flush data to disk, set the NoData value and calculate stats
#     outBand.FlushCache()
#     # outBand.SetNoDataValue(-9999)

#     # georeference the image and set the projection
#     outDs.SetGeoTransform(gdal_data.GetGeoTransform())
#     outDs.SetProjection(gdal_data.GetProjection())


class ProcessingWallHeightAscpetAlgorithm():

    INPUT_LIMIT = 'INPUT_LIMIT'
    INPUT = 'INPUT'
    OUTPUT_HEIGHT = 'OUTPUT_HEIGHT'
    OUTPUT_ASPECT = 'OUTPUT_ASPECT'
    # ASPECT_BOOL = 'ASPECT_BOOL'


    def initAlgorithm(self):

        self.param_desc_dict = {
            self.INPUT: {'desc': 'Input building and ground DSM', 'type': str},
            # self.ASPECT_BOOL: {'desc': 'Calculate wall aspect', 'default': True},
            # self.addParameter(QgsProcessingParameterBoolean(self.ASPECT_BOOL,
            #     self.tr("Calculate wall aspect"),
            #     defaultValue=True)) 
            self.INPUT_LIMIT: {'desc':'Lower limit for wall height (m)', 'type': float, 'default': 3.0, 'min': 0.0},  
            self.OUTPUT_HEIGHT: {'desc': 'Output Wall Height Raster', 'type': str},
            self.OUTPUT_ASPECT: {'desc': 'Output Wall Aspect Raster', 'type': str, 'default':None}
            }

    def processAlgorithm(self, parameters):
        # aspectcalculation = self.parameterAsBool(parameters, self.ASPECT_BOOL, context)
        feedback = DummyFeedback()
        
        parameter_dict = self.set_wall_parameter(parameters)
        logger.info(f'Initiating algorithm with parameters {parameter_dict}')

        cmd_folder = Path(os.path.split(inspect.getfile(inspect.currentframe()))[0])
        logger.info(str(cmd_folder))
        logger.info(str(cmd_folder.parent))
        
        # feedback.setProgressText(str(parameters["INPUT"])) # this prints to the processing log tab
        # QgsMessageLog.logMessage("Testing", "umep", level=Qgis.Info) # This prints to a umep tab
        
        input = os.path.join(parameter_dict["input"])
        logger.debug(f"input is {input} {type(input)} {input is None}")
        # dem = self.parameterAsRasterLayer(parameters, self.INPUT_DEM, context)

        if input is None:
            raise ValueError("Error: No valid DEM selected")

        # load raster
        gdal.AllRegister()
        # provider = dem.dataProvider()
        filepath_dsm = input  # str(provider.dataSourceUri())
        gdal_dsm = gdal.Open(filepath_dsm)
        dsm = gdal_dsm.ReadAsArray().astype(float)

        # provider = dsm.dataProvider()
        # filepath_dsm = str(provider.dataSourceUri())
        # gdal_dsm = gdal.Open(filepath_dsm)
        # dsm = gdal_dsm.ReadAsArray().astype(float)
        
        logger.info("Calculating wall height")
        total = 100. / (int(dsm.shape[0] * dsm.shape[1]))
        walls = wa.findwalls(dsm, parameter_dict['inputLimit'], feedback, total)

        wallssave = np.copy(walls)
        saverasternd(gdal_dsm, parameter_dict['outputHeight'], wallssave)
        
        if parameter_dict['outputAspect'] != "None":
            total = 100. / 180.0
            # outputFileAspect = self.parameterAsOutputLayer(parameters, self.OUTPUT_ASPECT, context)
            logger.info("Calculating wall aspect")
            dirwalls = wa.filter1Goodwin_as_aspect_v3(walls, 1, dsm, feedback, total)
            saverasternd(gdal_dsm, parameter_dict['outputAspect'], dirwalls)
        else:
            logger.warn("Wall aspect not calculated")
        
        return {self.OUTPUT_HEIGHT: parameter_dict['outputHeight'], self.OUTPUT_ASPECT: parameter_dict['outputAspect']}

    def name(self):
        return 'Urban Geometry: Wall Height and Aspect'

    def displayName(self):
        return self.tr(self.name())

    def group(self):
        return self.tr(self.groupId())

    def groupId(self):
        return 'Pre-Processor'

    def shortHelpString(self):
        return self.tr('This algorithm identiies wall pixels and '
            'their height from ground and building digital surface models (DSM) by using a filter as '
            'presented by Lindberg et al. (2015a). Optionally, wall aspect can also be estimated using '
            'a specific linear filter as presented by Goodwin et al. (1999) and further developed by '
            'Lindberg et al. (2015b) to obtain the wall aspect. Wall aspect is given in degrees where '
            'a north facing wall pixel has a value of zero. The output of this plugin is used in other '
            'UMEP plugins such as SEBE (Solar Energy on Building Envelopes) and SOLWEIG (SOlar LongWave '
            'Environmental Irradiance Geometry model).\n'
            '------------------ \n'
            'Goodwin NR, Coops NC, Tooke TR, Christen A, Voogt JA (2009) Characterizing urban surface cover and structure with airborne lidar technology. Can J Remote Sens 35:297–309\n'
            'Lindberg F., Grimmond, C.S.B. and Martilli, A. (2015a) Sunlit fractions on urban facets - Impact of spatial resolution and approach Urban Climate DOI: 10.1016/j.uclim.2014.11.006\n'
            'Lindberg F., Jonsson, P. & Honjo, T. and Wästberg, D. (2015b) Solar energy on building envelopes - 3D modelling in a 2D environment Solar Energy 115 369–378'
            '-------------\n'
            'Full manual available via the <b>Help</b>-button.')

    def helpUrl(self):
        url = 'https://umep-docs.readthedocs.io/en/latest/pre-processor/Urban%20Geometry%20Wall%20Height%20and%20Aspect.html'
        return url

    def createInstance(self):
        return ProcessingWallHeightAscpetAlgorithm()
    
    def set_wall_parameter(self, parameters: Dict[str, Any]) -> Dict[str,Any]:
        """
        Evaluates the parameters with matching definition from 'parameters' to the expected format
        and checks ProcessingWallHeightAscpetAlgorithm boundary conditions

        Args:
            context: context of application
            parameters: dictionary of parameters

        Returns:
            dictionary of checked parameters

        """

        parameter_dict = {}
        # InputParameters
        parameter_dict["input"] = self._check_parameter(parameters, self.INPUT, check_dir=True)
        parameter_dict["inputLimit"] = self._check_parameter(parameters, self.INPUT_LIMIT)
        parameter_dict["outputHeight"] = self._check_parameter(parameters, self.OUTPUT_HEIGHT, check_dir=True)
        parameter_dict["outputAspect"] = self._check_parameter(parameters, self.OUTPUT_ASPECT, check_dir=True)

        return parameter_dict

    def _check_parameter(self, parameter_list, eigen_parameter, check_dir=False):
        try:
            value = parameter_list[eigen_parameter]
        except KeyError:
            if 'default' in self.param_desc_dict[eigen_parameter].keys():
                value = self.param_desc_dict[eigen_parameter]['default']
            else:
                raise KeyError
        expected_type = self.param_desc_dict[eigen_parameter]['type']
        logger.debug(f"{value} expected type {expected_type} Any? {expected_type is Any} matching? {isinstance(value, expected_type)} str? {expected_type == str}  tif? {'tif' in str(value)}")
        if expected_type is Any:
            return value

        elif isinstance(value, expected_type):
            if type(value) == str and check_dir:
                if not os.path.exists(str(value)):
                    raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), str(value))
            return value
        elif expected_type == str:
            return str(value)
        else:
            raise TypeError(f"Value and expected type did not match. "
                            f"Expected {expected_type}, got value of type {type(value)}")
