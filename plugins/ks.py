#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uproot
import numpy
import scipy.stats
from autodqm.plugin_results import PluginResults
import plotly.graph_objects as go

def comparators():
    return {
        "ks_test": ks
    }


def ks(histpair, ks_cut=0.09, min_entries=100000, **kwargs):

    data_name = histpair.data_name
    ref_name = histpair.ref_name

    data_hist = histpair.data_hist
    ref_hist = histpair.ref_hist

    # Check that the hists are histograms
    # Check that the hists are 1 dimensional
    if "1" not in str(type(data_hist)) or "1" not in str(type(ref_hist)):
        return None

    # Normalize data_hist
    data_hist_norm = numpy.copy(data_hist.allvalues)
    ref_hist_norm = numpy.copy(ref_hist.allvalues)
    if data_hist._fEntries > 0:
        data_hist_norm = data_hist_norm * (ref_hist._fEntries / data_hist._fEntries)

    # Reject empty histograms
    is_good = data_hist._fEntries != 0 and data_hist._fEntries >= min_entries

    ks = scipy.stats.kstest(ref_hist_norm, data_hist_norm)[0]

    is_outlier = is_good and ks > ks_cut


    bins = data_hist.alledges[:-1]
    if bins[0] < -999:
        bins[0]=2*bins[1]-bins[2]

    c = go.Figure()
    c.add_trace(go.Bar(name="data:"+str(histpair.data_run), x=bins, y=data_hist_norm, marker_color='white', marker=dict(line=dict(width=1,color='red'))))
    c.add_trace(go.Bar(name="ref:"+str(histpair.ref_run), x=bins, y=ref_hist_norm, marker_color='rgb(204, 188, 172)', opacity=.9))
    c['layout'].update(bargap=0)
    c['layout'].update(barmode='overlay')
    c['layout'].update(plot_bgcolor='white')
    c.update_xaxes(showline=True, linewidth=2, linecolor='black', mirror=True)
    c.update_yaxes(showline=True, linewidth=2, linecolor='black', mirror=True)
    c.update_layout(
        title=histpair.data_name + " KS Test " + histpair.data_run + " | " + histpair.ref_run,
        xaxis_title= data_hist._fXaxis._fTitle.decode('utf8'),
        yaxis_title= data_hist._fYaxis._fTitle.decode('utf8')
    )
    data_text = "ref:"+str(histpair.ref_run)
    ref_text = "data:"+str(histpair.data_run)
    artifacts = [data_hist_norm, ref_hist_norm, data_text, ref_text]

    info = {
        'Data_Entries': data_hist._fEntries,
        'Ref_Entries': ref_hist._fEntries,
        'KS_Val': ks
    }

    return PluginResults(
        c,
        show=is_outlier,
        info=info,
        artifacts=artifacts)
