#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import uproot
import numpy
from scipy.stats import chi2
from autodqm.plugin_results import PluginResults
import scipy
import plotly.graph_objects as go

def comparators():
    return {
        'pull_values': pullvals
    }


def pullvals(histpair,
             pull_cap=25, chi2_cut=500, pull_cut=20, min_entries=100000, norm_type='all',
             **kwargs):
    """Can handle poisson driven TH2s or generic TProfile2Ds"""
    data_hist = histpair.data_hist
    ref_hist = histpair.ref_hist

    # Check that the hists are histograms
    # Check that the hists are 2 dimensional
    if not "2" in str(type(data_hist)) or not "2" in str(type(ref_hist)):
        return None
    # Extract values from TH2F or TProfile2D Format
    data_hist_norm = None
    ref_hist_norm = None
    if "TProfile" in str(type(data_hist)):
        data_hist_norm = numpy.reshape(data_hist._fBinEntries, (data_hist.xnumbins+2, data_hist.ynumbins+2))
        ref_hist_norm = numpy.reshape(ref_hist._fBinEntries, (data_hist.xnumbins+2, data_hist.ynumbins+2))
    else:
        data_hist_norm = numpy.copy(data_hist.values)
        ref_hist_norm = numpy.copy(ref_hist.values)

    # Clone data_hist array to create pull_hist array to be filled later
    pull_hist = numpy.copy(data_hist_norm)


    # Reject empty histograms
    is_good = data_hist._fEntries != 0 and data_hist._fEntries >= min_entries

    # Normalize data_hist
    if norm_type == "row":
        data_hist_norm = normalize_rows(data_hist_norm, ref_hist_norm)
    else:
        if data_hist._fEntries > 0:
            data_hist_norm = data_hist_norm * ref_hist._fEntries / data_hist._fEntries

    data_hist_errs = numpy.nan_to_num(abs(numpy.array(scipy.stats.chi2.interval(0.6827, 2 * data_hist_norm)) / 2 - 1 - data_hist_norm))
    ref_hist_errs = numpy.nan_to_num(abs(numpy.array(scipy.stats.chi2.interval(0.6827, 2 * ref_hist_norm)) / 2 - 1 - ref_hist_norm))

    max_pull = 0
    nBins = 0
    chi2 = 0
    for x in range(0, data_hist_norm.shape[0]):
        for y in range(0, data_hist_norm.shape[1]):

            # Bin 1 data
            bin1 = data_hist_norm[x, y]

            # Bin 2 data
            bin2 = ref_hist_norm[x, y]

            # Getting Proper Poisson error 
            bin1err, bin2err = data_hist_errs[0, x, y], ref_hist_errs[1, x, y]
            if bin1 < bin2:
                bin1err, bin2err = data_hist_errs[1, x, y], ref_hist_errs[0, x, y]
            # Count bins for chi2 calculation
            nBins += 1

            # Ensure that divide-by-zero error is not thrown when calculating pull
            if bin1err == 0 and bin2err == 0:
                new_pull = 0
            else:
                new_pull = pull(bin1, bin1err, bin2, bin2err)

            # Sum pulls
            chi2 += new_pull**2

            # Check if max_pull
            max_pull = max(max_pull, abs(new_pull))

            # Clamp the displayed value
            fill_val = max(min(new_pull, pull_cap), -pull_cap)

            # If the input bins were explicitly empty, make this bin white by
            # setting it out of range
            if bin1 == bin2 == 0:
                fill_val = -999

            # Fill Pull Histogram            
            pull_hist[x, y] = fill_val

    # Compute chi2
    chi2 = (chi2 / nBins)

    is_outlier = is_good and (chi2 > chi2_cut or abs(max_pull) > pull_cut)

    # Set up canvas
    pull_hist = numpy.where(pull_hist < -2*pull_cap, None, pull_hist)
    colors = ['rgb(26, 42, 198)', 'rgb(118, 167, 231)', 'rgb(215, 226, 194)', 'rgb(212, 190, 109)', 'rgb(188, 76, 38)']

    xLabels = None
    yLabels = None
    c = None
    if data_hist._fXaxis._fLabels:
       xLabels = [str(x) for x in data_hist._fXaxis._fLabels]
    else:
       xLabels = [str(data_hist.xlow + x*(data_hist.xhigh-data_hist.xlow)/pull_hist.shape[1]) for x in range(0,pull_hist.shape[0])]
    if data_hist._fYaxis._fLabels:
       yLabels = [str(x) for x in data_hist._fYaxis._fLabels]
    else:
       yLabels = [str(data_hist.ylow + x*(data_hist.yhigh-data_hist.ylow)/pull_hist.shape[1]) for x in range(0,pull_hist.shape[1])]

    if pull_hist.shape[1] != len(xLabels):
         pull_hist = numpy.transpose(pull_hist)

    c  = go.Figure(data=go.Heatmap(z=pull_hist, zmin=-pull_cap, zmax=pull_cap, colorscale=colors,x=xLabels, y=yLabels))
    c['layout'].update(plot_bgcolor='white')
    c.update_xaxes(showline=True, linewidth=2, linecolor='black', mirror=True)
    c.update_yaxes(showline=True, linewidth=2, linecolor='black', mirror=True)
    c.update_layout(
        title=histpair.data_name + " Pull Values",
        xaxis_title= data_hist._fXaxis._fTitle.decode('utf8'),
        yaxis_title= data_hist._fYaxis._fTitle.decode('utf8')
    )

    info = {
        'Chi_Squared': chi2,
        'Max_Pull_Val': max_pull,
        'Data_Entries': data_hist._fEntries,
        'Ref_Entries': ref_hist._fEntries,
    }

    artifacts = [pull_hist, str(data_hist._fEntries), str(ref_hist._fEntries)]

    return PluginResults(
        c,
        show=bool(is_outlier),
        info=info,
        artifacts=artifacts)


def pull(bin1, binerr1, bin2, binerr2):
    ''' Calculate the pull value between two bins.
        pull = (data - expected)/sqrt(sum of errors in quadrature))
        data = |bin1 - bin2|, expected = 0
    '''
    return (bin1 - bin2) / ((binerr1**2 + binerr2**2)**0.5)

def normalize_rows(data_hist_norm, ref_hist_norm):

    for y in range(0, ref_hist_norm.shape[1]):

        # Stores sum of row elements
        rrow = 0
        frow = 0

        # Sum over row elements
        for x in range(0, ref_hist_norm.shape[0]):

            # Bin data
            rbin = ref_hist_norm[x,y]
            fbin = data_hist_norm[x, y]

            rrow += rbin
            frow += fbin

        # Scaling factors
        # Prevent divide-by-zero error
        if frow == 0:
            frow = 1
        if frow > 0:
            sf = float(rrow) / frow
        else:
            sf = 1
        # Prevent scaling everything to zero
        if sf == 0:
            sf = 1

        # Normalization
        for x in range(0, ref_hist_norm.shape[0]):
            # Bin data
            fbin = data_hist_norm[x, y]
            fbin_err = (fbin)**(.5)

            # Normalize bin
            data_hist_norm[x, y] = (fbin * sf)
    return data_hist_norm

