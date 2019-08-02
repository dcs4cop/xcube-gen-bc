# The MIT License (MIT)
# Copyright (c) 2019 by the xcube development team and contributors
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from abc import ABCMeta
from typing import Tuple

import numpy as np
import xarray as xr

from xcube.util.constants import CRS_WKT_EPSG_4326
from xcube.util.timecoord import to_time_in_days_since_1970
from .transexpr import translate_snap_expr_attributes
from .vectorize import vectorize_wavebands, new_band_coord_var
from xcube.api.gen.iproc import XYInputProcessor, ReprojectionInfo, register_input_processor


class SnapNetcdfInputProcessor(XYInputProcessor, metaclass=ABCMeta):
    """
    Input processor for SNAP L2 NetCDF inputs.
    """

    @property
    def input_reader(self) -> str:
        return 'netcdf4'

    @property
    def input_reader_params(self) -> dict:
        return dict(decode_cf=True, decode_coords=True, decode_times=False)

    def get_reprojection_info(self, dataset: xr.Dataset) -> ReprojectionInfo:
        return ReprojectionInfo(xy_var_names=('lon', 'lat'),
                                xy_tp_var_names=('TP_longitude', 'TP_latitude'),
                                xy_crs=CRS_WKT_EPSG_4326,
                                xy_gcp_step=5)

    def get_time_range(self, dataset: xr.Dataset) -> Tuple[float, float]:

        if "time_coverage_start" in dataset.attrs:
            t1 = str(dataset.attrs["time_coverage_start"])
            t2 = str(dataset.attrs.get("time_coverage_end", t1))
        else:
            t1 = dataset.attrs.get('start_date')
            t2 = dataset.attrs.get('stop_date', t1)
        if t1 is None or t2 is None:
            raise ValueError('illegal L2 input: missing start/stop time')
        t1 = to_time_in_days_since_1970(t1)
        t2 = to_time_in_days_since_1970(t2)
        return t1, t2

    def pre_process(self, dataset: xr.Dataset) -> xr.Dataset:
        """ Do any pre-processing before reprojection. """
        return translate_snap_expr_attributes(dataset)

    def post_process(self, dataset: xr.Dataset) -> xr.Dataset:
        def new_band_coord_var_ex(band_dim_name: str, band_values: np.ndarray) -> xr.DataArray:
            # Bug in HIGHROC OLCI L2 data: both bands 20 and 21 have wavelengths at 940 nm
            if band_values[-2] == band_values[-1] and band_values[-1] == 940.:
                band_values[-1] = 1020.
            return new_band_coord_var(band_dim_name, band_values)

        return vectorize_wavebands(dataset, new_band_coord_var_ex)


# noinspection PyAbstractClass
class SnapOlciHighrocL2InputProcessor(SnapNetcdfInputProcessor):
    """
    Input processor for SNAP Sentinel-3 OLCI HIGHROC Level-2 NetCDF inputs.
    """

    @property
    def name(self) -> str:
        return 'snap-olci-highroc-l2'

    @property
    def description(self) -> str:
        return 'SNAP Sentinel-3 OLCI HIGHROC Level-2 NetCDF inputs'


# noinspection PyAbstractClass
class SnapOlciCyanoAlertL2InputProcessor(SnapNetcdfInputProcessor):
    """
    Input processor for SNAP Sentinel-3 OLCI HIGHROC Level-2 NetCDF inputs.
    """

    @property
    def name(self) -> str:
        return 'snap-olci-cyanoalert-l2'

    @property
    def description(self) -> str:
        return 'SNAP Sentinel-3 OLCI CyanoAlert Level-2 NetCDF inputs'


def init_plugin():
    """ Register a DatasetIO object: SnapOlciHighrocL2NetcdfInputProcessor() """
    register_input_processor(SnapOlciHighrocL2InputProcessor())
    register_input_processor(SnapOlciCyanoAlertL2InputProcessor())
