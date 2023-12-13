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

from osgeo import gdal, osr
from osgeo.gdalconst import *
import os
import numpy as np


import zipfile
import sys
from util import misc
from functions import svf_functions_standalone as svf
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)
FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
# logging.basicConfig(format=FORMAT)
logger.setLevel(logging.WARNING)
logger.propagate = False


class ProcessingSkyViewFactorAlgorithm():
    """
    This algorithm is a processing version of SkyViewFactor
    """

    INPUT_DSM = 'INPUT_DSM'
    INPUT_CDSM = 'INPUT_CDSM'
    INPUT_TDSM = 'INPUT_TDSM'
    # USE_VEG = 'USE_VEG'
    TRANS_VEG = 'TRANS_VEG'
    # TSDM_EXIST = 'TSDM_EXIST'
    INPUT_THEIGHT = 'INPUT_THEIGHT'
    ANISO = 'ANISO'
    OUTPUT_DIR = 'OUTPUT_DIR'
    OUTPUT_FILE = 'OUTPUT_FILE'
    
    def initAlgorithm(self):
        logger.info("Init SkyViewFactor Algorithm")
        self.param_desc_dict = {
            #spatial
            self.INPUT_DSM: {'desc': 'Building and ground Digital Surface Model (DSM)', 'type': str},
            self.INPUT_CDSM: {'desc': 'Vegetation Canopy DSM', 'type': str, 'default': None},
            self.TRANS_VEG: {'desc': 'Transmissivity of light through vegetation (%):', 'type': int, 'min':0, 'max':100, 'default': 3},
            self.INPUT_TDSM: {'desc': 'Vegetation Trunk-zone DSM', 'type': str, 'default': None},
            self.INPUT_THEIGHT: {'desc': "Trunk zone height (percent of Canopy Height). Used if no Vegetation Trunk-zone DSM is loaded", 'type': float, 'min': 0.1, 'max': 99.9, 'default': 25.0},
            self.ANISO: {'desc': 'Use method with 153 shadow images instead of 655. Required for anisotropic sky scheme (SOLWEIG)', 'type':bool, 'default': False},
            self.OUTPUT_DIR: {'desc': 'Output folder for individual raster files', 'type': str},
            self.OUTPUT_FILE: {'desc': 'Output sky view factor raster', 'type': str}
        }

    def processAlgorithm(self, parameters):
        # InputParameters
        # outputDir = self.parameterAsString(parameters, self.OUTPUT_DIR, context)
        # outputFile = self.parameterAsOutputLayer(parameters, self.OUTPUT_FILE, context)
        # dsmlayer = self.parameterAsRasterLayer(parameters, self.INPUT_DSM, context)
        # # useVegdem = self.parameterAsBool(parameters, self.USE_VEG, context)
        # transVeg = self.parameterAsDouble(parameters, self.TRANS_VEG, context)
        # vegdsm = self.parameterAsRasterLayer(parameters, self.INPUT_CDSM, context)
        # vegdsm2 = self.parameterAsRasterLayer(parameters, self.INPUT_TDSM, context)
        # # tdsmExists = self.parameterAsBool(parameters, self.TSDM_EXIST, context)
        # trunkr = self.parameterAsDouble(parameters, self.INPUT_THEIGHT, context)
        # aniso = self.parameterAsBool(parameters, self.ANISO, context)

        parameter_dict = self.set_svf_parameter(parameters)

        logger.info(f'Initiating algorithm with parameters {parameter_dict}')

        if parameters['OUTPUT_DIR'] == 'TEMPORARY_OUTPUT':
            if not (os.path.isdir(parameter_dict["outputDir"])):
                os.mkdir(parameter_dict["outputDir"])

        # provider = dsmlayer.dataProvider()
        # filepath_dsm = str(provider.dataSourceUri())
        gdal_dsm = gdal.Open(os.path.join(os.getcwd(), parameter_dict["dsmlayer"]))  # filepath_dsm)
        dsm = gdal_dsm.ReadAsArray().astype(float)

        # response to issue #85
        nd = gdal_dsm.GetRasterBand(1).GetNoDataValue()
        dsm[dsm == nd] = 0.
        if dsm.min() < 0:
            dsm = dsm + np.abs(dsm.min())

        sizex = dsm.shape[0]
        sizey = dsm.shape[1]

        geotransform = gdal_dsm.GetGeoTransform()
        scale = 1 / geotransform[1]
        
        trans = parameter_dict["transVeg"] / 100.0

        if parameter_dict["vegdsm"] != "None":
            usevegdem = 1
            logger.info('Vegetation scheme activated')
            # vegdsm = self.parameterAsRasterLayer(parameters, self.INPUT_CDSM, context)
            # if vegdsm is None:
                # raise QgsProcessingException("Error: No valid vegetation DSM selected")

            # load raster
            gdal.AllRegister()
            # provider = vegdsm.dataProvider()
            # filePathOld = str(provider.dataSourceUri())
            dataSet = gdal.Open(os.path.join(os.getcwd(), parameter_dict["vegdsm"]))  # filePathOld)
            vegdsm = dataSet.ReadAsArray().astype(float)

            vegsizex = vegdsm.shape[0]
            vegsizey = vegdsm.shape[1]

            if not (vegsizex == sizex) & (vegsizey == sizey):
                raise ValueError("Error in Vegetation Canopy DSM: All rasters must be of same extent and resolution")

            if parameter_dict["vegdsm2"] != "None":
                # vegdsm2 = self.parameterAsRasterLayer(parameters, self.INPUT_TDSM, context)
                # if vegdsm2 is None:
                    # raise QgsProcessingException("Error: No valid Trunk zone DSM selected")

                # load raster
                gdal.AllRegister()
                # provider = vegdsm2.dataProvider()
                # filePathOld = str(provider.dataSourceUri())
                dataSet = gdal.Open(parameter_dict["vegdsm2"])  # filePathOld)
                vegdsm2 = dataSet.ReadAsArray().astype(float)
            else:
                trunkratio = parameter_dict["trunkr"] / 100.0
                vegdsm2 = vegdsm * trunkratio

            vegsizex = vegdsm2.shape[0]
            vegsizey = vegdsm2.shape[1]

            if not (vegsizex == sizex) & (vegsizey == sizey):
                raise ValueError("Error in Trunk Zone DSM: All rasters must be of same extent and resolution")
        else:
            rows = dsm.shape[0]
            cols = dsm.shape[1]
            vegdsm = np.zeros([rows, cols])
            vegdsm2 = 0.
            usevegdem = 0

        logger.debug(f"aniso is {parameter_dict['aniso']} {parameter_dict['aniso']  is not None}")
        if parameter_dict["aniso"] != "None":  # == 1:
            logger.info('Calculating SVF using 153 iterations')
            ret = svf.svfForProcessing153(dsm, vegdsm, vegdsm2, scale, usevegdem)
        else:
            logger.info('Calculating SVF using 655 iterations')
            ret = svf.svfForProcessing655(dsm, vegdsm, vegdsm2, scale, usevegdem)

        filename = parameter_dict["outputFile"]

        # temporary fix for mac, ISSUE #15
        pf = sys.platform
        outputDir = os.path.join(os.getcwd(), parameter_dict["outputDir"])
        if pf == 'darwin' or pf == 'linux2' or pf == 'linux':
            if not os.path.exists(outputDir):
                os.makedirs(outputDir)

        if ret is not None:
            svfbu = ret["svf"]
            svfbuE = ret["svfE"]
            svfbuS = ret["svfS"]
            svfbuW = ret["svfW"]
            svfbuN = ret["svfN"]
            
            misc.saveraster(gdal_dsm, outputDir + '/' + 'svf.tif', svfbu)
            misc.saveraster(gdal_dsm, outputDir + '/' + 'svfE.tif', svfbuE)
            misc.saveraster(gdal_dsm, outputDir + '/' + 'svfS.tif', svfbuS)
            misc.saveraster(gdal_dsm, outputDir + '/' + 'svfW.tif', svfbuW)
            misc.saveraster(gdal_dsm, outputDir + '/' + 'svfN.tif', svfbuN)

            if os.path.isfile(outputDir + '/' + 'svfs.zip'):
                os.remove(outputDir + '/' + 'svfs.zip')

            zippo = zipfile.ZipFile(outputDir + '/' + 'svfs.zip', 'a')
            zippo.write(outputDir + '/' + 'svf.tif', 'svf.tif')
            zippo.write(outputDir + '/' + 'svfE.tif', 'svfE.tif')
            zippo.write(outputDir + '/' + 'svfS.tif', 'svfS.tif')
            zippo.write(outputDir + '/' + 'svfW.tif', 'svfW.tif')
            zippo.write(outputDir + '/' + 'svfN.tif', 'svfN.tif')
            zippo.close()

            os.remove(outputDir + '/' + 'svf.tif')
            os.remove(outputDir + '/' + 'svfE.tif')
            os.remove(outputDir + '/' + 'svfS.tif')
            os.remove(outputDir + '/' + 'svfW.tif')
            os.remove(outputDir + '/' + 'svfN.tif')

            if usevegdem == 0:
                svftotal = svfbu
            else:
                # report the result
                svfveg = ret["svfveg"]
                svfEveg = ret["svfEveg"]
                svfSveg = ret["svfSveg"]
                svfWveg = ret["svfWveg"]
                svfNveg = ret["svfNveg"]
                svfaveg = ret["svfaveg"]
                svfEaveg = ret["svfEaveg"]
                svfSaveg = ret["svfSaveg"]
                svfWaveg = ret["svfWaveg"]
                svfNaveg = ret["svfNaveg"]

                misc.saveraster(gdal_dsm, outputDir + '/' + 'svfveg.tif', svfveg)
                misc.saveraster(gdal_dsm, outputDir + '/' + 'svfEveg.tif', svfEveg)
                misc.saveraster(gdal_dsm, outputDir + '/' + 'svfSveg.tif', svfSveg)
                misc.saveraster(gdal_dsm, outputDir + '/' + 'svfWveg.tif', svfWveg)
                misc.saveraster(gdal_dsm, outputDir + '/' + 'svfNveg.tif', svfNveg)
                misc.saveraster(gdal_dsm, outputDir + '/' + 'svfaveg.tif', svfaveg)
                misc.saveraster(gdal_dsm, outputDir + '/' + 'svfEaveg.tif', svfEaveg)
                misc.saveraster(gdal_dsm, outputDir + '/' + 'svfSaveg.tif', svfSaveg)
                misc.saveraster(gdal_dsm, outputDir + '/' + 'svfWaveg.tif', svfWaveg)
                misc.saveraster(gdal_dsm, outputDir + '/' + 'svfNaveg.tif', svfNaveg)

                zippo = zipfile.ZipFile(outputDir + '/' + 'svfs.zip', 'a')
                zippo.write(outputDir + '/' + 'svfveg.tif', 'svfveg.tif')
                zippo.write(outputDir + '/' + 'svfEveg.tif', 'svfEveg.tif')
                zippo.write(outputDir + '/' + 'svfSveg.tif', 'svfSveg.tif')
                zippo.write(outputDir + '/' + 'svfWveg.tif', 'svfWveg.tif')
                zippo.write(outputDir + '/' + 'svfNveg.tif', 'svfNveg.tif')
                zippo.write(outputDir + '/' + 'svfaveg.tif', 'svfaveg.tif')
                zippo.write(outputDir + '/' + 'svfEaveg.tif', 'svfEaveg.tif')
                zippo.write(outputDir + '/' + 'svfSaveg.tif', 'svfSaveg.tif')
                zippo.write(outputDir + '/' + 'svfWaveg.tif', 'svfWaveg.tif')
                zippo.write(outputDir + '/' + 'svfNaveg.tif', 'svfNaveg.tif')
                zippo.close()

                os.remove(outputDir + '/' + 'svfveg.tif')
                os.remove(outputDir + '/' + 'svfEveg.tif')
                os.remove(outputDir + '/' + 'svfSveg.tif')
                os.remove(outputDir + '/' + 'svfWveg.tif')
                os.remove(outputDir + '/' + 'svfNveg.tif')
                os.remove(outputDir + '/' + 'svfaveg.tif')
                os.remove(outputDir + '/' + 'svfEaveg.tif')
                os.remove(outputDir + '/' + 'svfSaveg.tif')
                os.remove(outputDir + '/' + 'svfWaveg.tif')
                os.remove(outputDir + '/' + 'svfNaveg.tif')

                trans = parameter_dict["transVeg"] / 100.0
                svftotal = (svfbu - (1 - svfveg) * (1 - trans))

            misc.saveraster(gdal_dsm, filename, svftotal)

            # Save shadow images for SOLWEIG 2019a
            if parameter_dict["aniso"] != "None":  # == 1:
                shmat = ret["shmat"]
                vegshmat = ret["vegshmat"]
                vbshvegshmat = ret["vbshvegshmat"]
                # wallshmat = ret["wallshmat"]
                # wallsunmat = ret["wallsunmat"]
                # wallshvemat = ret["wallshvemat"]
                # facesunmat = ret["facesunmat"]

                np.savez_compressed(outputDir + '/' + "shadowmats.npz", shadowmat=shmat, vegshadowmat=vegshmat, vbshmat=vbshvegshmat) #,
                                    # vbshvegshmat=vbshvegshmat, wallshmat=wallshmat, wallsunmat=wallsunmat,
                                    # facesunmat=facesunmat, wallshvemat=wallshvemat)

        logger.info("Sky View Factor: SVF grid(s) successfully generated")

        return {self.OUTPUT_DIR: outputDir, self.OUTPUT_FILE: parameter_dict["outputFile"]}
    
    def name(self):
        return 'Urban Geometry: Sky View Factor'

    def displayName(self):
        return self.tr(self.name())

    def group(self):
        return self.tr(self.groupId())

    def groupId(self):
        return 'Pre-Processor'

    def shortHelpString(self):
        return self.tr('The Sky View Factor algorithm can be used to generate pixel wise sky view factor (SVF) '
        'using ground and building digital surface models (DSM). Optionally, vegetation DSMs could also be used. '
        'By definition, SVF is the ratio of the radiation received (or emitted) by a planar surface to the '
        'radiation emitted (or received) by the entire hemispheric environment (Watson and Johnson 1987). '
        'It is a dimensionless measure between zero and one, representing totally obstructed and free spaces, '
        'respectively. The methodology that is used to generate SVF here is described in Lindberg and Grimmond (2010).\n'
        '-------------\n'
        'Lindberg F, Grimmond CSB (2010) Continuous sky view factor maps from high resolution urban digital elevation models. Clim Res 42:177–183\n'
        'Watson ID, Johnson GT (1987) Graphical estimation of skyview-factors in urban environments. J Climatol 7: 193–197'
        '------------\n'
        'Full manual available via the <b>Help</b>-button.')

    def helpUrl(self):
        url = "https://umep-docs.readthedocs.io/en/latest/pre-processor/Urban%20Geometry%20Sky%20View%20Factor%20Calculator.html"
        return url

    # def tr(self, string):
    #     return QCoreApplication.translate('Processing', string)
    #
    # def icon(self):
    #     cmd_folder = Path(os.path.split(inspect.getfile(inspect.currentframe()))[0]).parent
    #     icon = QIcon(str(cmd_folder) + "/icons/icon_svf.png")
    #     return icon

    def createInstance(self):
        return ProcessingSkyViewFactorAlgorithm()

    def set_svf_parameter(self, parameters: Dict[str, Any]) -> Dict[str,Any]:
        """
        Evaluates the parameters with matching definition from 'parameters' to the expected format
        and checks ProcessingSkyViewFactorAlgorithm boundary conditions

        Args:
            context: context of application
            parameters: dictionary of parameters

        Returns:
            dictionary of checked parameters

        """

        parameter_dict = {}
        # InputParameters
        parameter_dict["dsmlayer"] = self._check_parameter(parameters, self.INPUT_DSM)
        parameter_dict["vegdsm"] = self._check_parameter(parameters, self.INPUT_CDSM)
        parameter_dict["transVeg"] = self._check_parameter(parameters, self.TRANS_VEG)
        parameter_dict["vegdsm2"] = self._check_parameter(parameters, self.INPUT_TDSM)
        parameter_dict["trunkr"] = self._check_parameter(parameters, self.INPUT_THEIGHT)
        parameter_dict["aniso"] = self._check_parameter(parameters, self.ANISO)
        parameter_dict["outputDir"] = self._check_parameter(parameters, self.OUTPUT_DIR)
        parameter_dict["outputFile"] = self._check_parameter(parameters, self.OUTPUT_FILE)

        return parameter_dict

    def _check_parameter(self, parameter_list, eigen_parameter):
        value = parameter_list[eigen_parameter]
        expected_type = self.param_desc_dict[eigen_parameter]['type']
        logger.debug(f"{value} expected type {expected_type} Any? {expected_type is Any} matching? {isinstance(value, expected_type)} str? {expected_type == str}  tif? {'tif' in str(value)}")
        if expected_type is Any:
            return value

        elif isinstance(value, expected_type):
            return value
        elif expected_type == str:
            return str(value)

        else:
            raise TypeError(f"Value and expected type did not match. "
                            f"Expected {expected_type}, got value of type {type(value)}")
