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

from qgis.PyQt.QtCore import QCoreApplication, QDate, Qt, QVariant
from qgis.core import (QgsProcessing,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterPoint,
                       QgsProcessingParameterString,
                       QgsProcessingParameterBoolean,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterFolderDestination,
                       QgsProcessingParameterCrs,
                       QgsProcessingException)

from processing.gui.wrappers import WidgetWrapper
from qgis.PyQt.QtWidgets import QDateEdit

# from processing.gui.wrappers import WidgetWrapper
from qgis.PyQt.QtWidgets import QDateEdit, QTimeEdit
from qgis.PyQt.QtGui import QIcon
from osgeo import gdal, osr, ogr
from osgeo.gdalconst import *
import os
import numpy as np
import inspect
from pathlib import Path
# import zipfile
import sys
# from ..util import misc
# # from ..functions import svf_functions as svf
# from osgeo import gdal
# import subprocess
import datetime
# import webbrowser
import supy as sp
import logging


class ProcessingCopernicusERA5Algorithm(QgsProcessingAlgorithm):
    """
    This algorithm is a processing version of Image Morphometric Calculator Point
    """

    INPUT_POINT = 'INPUT_POINT'
    CRS = 'CRS'
    DATEINISTART = 'DATEINISTART'
    DATEINIEND = 'DATEINIEND'
    OUTPUT_DIR = 'OUTPUT_DIR'

    
    def initAlgorithm(self, config):
        self.addParameter(QgsProcessingParameterPoint(self.INPUT_POINT,
            self.tr('Point of interest')))
        self.addParameter(QgsProcessingParameterCrs(self.CRS,
            self.tr('Coordinate reference system for point of interest'), 'ProjectCrs'))
        paramS = QgsProcessingParameterString(self.DATEINISTART, 'Start date')
        paramS.setMetadata({'widget_wrapper': {'class': DateWidgetStart}})
        self.addParameter(paramS)
        paramE = QgsProcessingParameterString(self.DATEINIEND, 'End date')
        paramE.setMetadata({'widget_wrapper': {'class': DateWidgetEnd}})
        self.addParameter(paramE)
        self.addParameter(QgsProcessingParameterFolderDestination(self.OUTPUT_DIR, 
            self.tr('Output folder')))


    def processAlgorithm(self, parameters, context, feedback):
        # InputParameters
        inputPoint = self.parameterAsPoint(parameters, self.INPUT_POINT, context)
        # inputPoint = self.parameterAsString(parameters, self.INPUT_POINT, context)
        inputCRS = self.parameterAsCrs(parameters, self.CRS, context)
        startDate = self.parameterAsString(parameters, self.DATEINISTART, context)
        endDate = self.parameterAsString(parameters, self.DATEINIEND, context)
        outputDir = self.parameterAsString(parameters, self.OUTPUT_DIR, context)

        if parameters['OUTPUT_DIR'] == 'TEMPORARY_OUTPUT':
            if not (os.path.isdir(outputDir)):
                os.mkdir(outputDir)

        # Get POI in latlon
        old_cs = osr.SpatialReference()
        crs_ref = inputCRS.toWkt()
        old_cs.ImportFromWkt(crs_ref)

        x = float(inputPoint[0])
        y = float(inputPoint[1])

        # feedback.setProgressText("x = " + str(old_cs))

        # feedback.setProgressText("x = " + str(x))
        # feedback.setProgressText("y = " + str(y))

        wgs84_wkt = """
        GEOGCS["WGS 84",
            DATUM["WGS_1984",
                SPHEROID["WGS 84",6378137,298.257223563,
                    AUTHORITY["EPSG","7030"]],
                AUTHORITY["EPSG","6326"]],
            PRIMEM["Greenwich",0,
                AUTHORITY["EPSG","8901"]],
            UNIT["degree",0.01745329251994328,
                AUTHORITY["EPSG","9122"]],
            AUTHORITY["EPSG","4326"]]"""

        new_cs = osr.SpatialReference()
        new_cs.ImportFromWkt(wgs84_wkt)
    
        transform = osr.CoordinateTransformation(old_cs, new_cs)

        latlon = ogr.CreateGeometryFromWkt(
            'POINT (' + str(x) + ' ' + str(y) + ')')
        latlon.Transform(transform)

        gdalver = float(gdal.__version__[0])
        if gdalver == 3.:
            lon = latlon.GetY()
            lat = latlon.GetX()
        else:
            lat = latlon.GetY()
            lon = latlon.GetX()
            
        feedback.setProgressText('lat = ' + str(lat))
        feedback.setProgressText('lon = ' + str(lon))
        feedback.setProgressText('Start = ' + str(startDate))
        feedback.setProgressText('End = ' + str(endDate))
        feedback.setProgressText(outputDir)

        if startDate >= endDate:
            raise QgsProcessingException('Start date is greater or equal than end date')
       
        logger_sp = logging.getLogger('SuPy')
        logger_sp.disabled = True

        # feedback.setProgressText(str(sys.stdout))
            
        sp.util.gen_forcing_era5(lat, lon, startDate, endDate, dir_save=outputDir)

        results = {self.OUTPUT_DIR: outputDir}

        return results
    
    def name(self):
        return 'Meteorological Data: Download data (ERA5)'

    def displayName(self):
        return self.tr(self.name())

    def group(self):
        return self.tr(self.groupId())

    def groupId(self):
        return 'Pre-Processor'

    def shortHelpString(self):
        return self.tr('Basic meteorological variables are required for most applications in the UMEP processor. If observed data are not available for a particular location, hourly data can be retrieved from the global the Coopernicus programme and thier Climate Data Store. This plugin allows climate reanalysis data to be extracted for a specific location and period of interest (1979-2020), and transformed into formatted forcing files suitable for models within UMEP.'
        '\n'
        '---------------\n'
        'Full manual available via the <b>Help</b>-button.')

    def helpUrl(self):
        url = "https://umep-docs.readthedocs.io/en/latest/pre-processor/Meteorological%20Data%20Download%20data%20(ERA5).html"
        return url

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def icon(self):
        cmd_folder = Path(os.path.split(inspect.getfile(inspect.currentframe()))[0]).parent
        icon = QIcon(str(cmd_folder) + "/icons/watch.png")
        return icon

    def createInstance(self):
        return ProcessingCopernicusERA5Algorithm()


class DateWidgetStart(WidgetWrapper):
    def createWidget(self):
        self._combo = QDateEdit()
        self._combo.setCalendarPopup(True)

        today = QDate(2000, 1, 1)
        self._combo.setDate(today)

        return self._combo

    def value(self):
        date_chosen = self._combo.dateTime()
        return date_chosen.toString(Qt.ISODate)

class DateWidgetEnd(WidgetWrapper):
    def createWidget(self):
        self._combo = QDateEdit()
        self._combo.setCalendarPopup(True)

        today = QDate(2000, 1, 2)
        self._combo.setDate(today)

        return self._combo

    def value(self):
        date_chosen = self._combo.dateTime()
        return date_chosen.toString(Qt.ISODate)