import numpy as np
import matplotlib.pyplot as plt
from matplotlib import gridspec
from ..stats import hpd, gelman_rubin, effective_n
from ..utils import trace_to_dataframe, expand_variable_names
from .plot_utils import _scale_text


def forestplot(trace, models=None, varnames=None, alpha=0.05, quartiles=True, rhat=True, neff=True,
               main=None, xtitle=None, xlim=None, ylabels=None, colors='C0', chain_spacing=0.1,
               vline=0, figsize=None, textsize=None, skip_first=0, plot_kwargs=None, gs=None):
    """
    Forest plot

    Generates a forest plot of 100*(1-alpha)% credible intervals from a trace or list of traces.

    Parameters
    ----------
    trace : trace or list of traces
        Trace(s) from an MCMC sample
    models : list of strings (optional)
        List with names for the models in the list of traces. Useful when plotting more that one
        trace
    varnames: list, optional
        List of variables to plot (defaults to None, which results in all variables plotted)
    alpha : float, optional
        Alpha value for (1-alpha)*100% credible intervals. Defaults to 0.05.
    quartiles : bool, optional
        Flag for plotting the interquartile range, in addition to the (1-alpha)*100% intervals.
        Defaults to True
    rhat : bool, optional
        Flag for plotting Gelman-Rubin statistics. Requires 2 or more chains. Defaults to True
    neff : bool, optional
        Flag for plotting the effective sample size. Requires 2 or more chains. Defaults to True
    main : string, optional
        Title for main plot. Passing False results in titles being suppressed. Defaults to None
    xtitle : string, optional
        Label for x-axis. Defaults to None, i.e. no label
    xlim : list or tuple, optional
        Range for x-axis. Defaults to None, i.e. matplotlib's best guess.
    ylabels : list or array, optional
        User-defined labels for each variable. If not provided, the node
        __name__ attributes are used
    colors : list or string, optional
        list with valid matplotlib colors, one color per model. Alternative a string can be passed.
        If the string is `cycle`, it will automatically chose a color per model from the
        matyplolibs cycle. If a single color is passed, eg 'k', 'C2', 'red' this color will be used
        for all models. Defauls to 'C0' (blueish in most matplotlib styles)
    chain_spacing : float, optional
        Plot spacing between chains. Defaults to 0.1
    vline : numeric, optional
        Location of vertical reference line. Defaults to 0
    figsize : tuple, optional
        Figure size. Defaults to None
    textsize: int
        Text size for labels. If None it will be autoscaled based on figsize.
    skip_first : int
        Number of first samples not shown in plots (burn-in).
    plot_kwargs : dict, optional
        Optional arguments for plot elements. Currently accepts `fontsize`, `linewidth`, `marker`
        and `markersize`.
    gs : GridSpec
        Matplotlib GridSpec object. Defaults to None.

    Returns
    -------
    gs : matplotlib GridSpec

    """
    if plot_kwargs is None:
        plot_kwargs = {}

    if not isinstance(trace, (list, tuple)):
        trace = [trace_to_dataframe(trace[skip_first:], combined=False)]
    else:
        trace = [trace_to_dataframe(tr[skip_first:], combined=False) for tr in trace]

    if models is None:
        if len(trace) > 1:
            models = ['m_{}'.format(i) for i in range(len(trace))]
        else:
            models = ['']
    elif len(models) != len(trace):
        raise ValueError("The number of names for the models does not match the number of models")

    if colors == 'cycle':
        colors = ['C{}'.format(i % 10) for i in range(len(models))]
    elif isinstance(colors, str):
        colors = [colors for i in range(len(models))]

    # Quantiles to be calculated
    if quartiles:
        qlist = [alpha / 2, 0.25, 0.50, 0.75,  (1 - alpha / 2)]
    else:
        qlist = [alpha / 2, 0.50, (1 - alpha / 2)]

    nchains = [tr.columns.value_counts()[0] for tr in trace]

    if varnames is None:
        varnames = []
        for tr in trace:
            varnames_tmp = tr.columns
            for v in varnames_tmp:
                if v not in varnames:
                    varnames.append(v)
    else:
        v_tmp = []
        for tr in trace:
            v_tmp.extend(expand_variable_names(tr, varnames))
        varnames = np.unique(v_tmp)

    plot_rhat = [rhat and nch > 1 for nch in nchains]
    plot_neff = [neff and nch > 1 for nch in nchains]


    if figsize is None:
        figsize = (6, len(varnames) * 2)

    textsize, linewidth, ms = _scale_text(figsize, textsize=textsize)

    fig = plt.figure(figsize=figsize)

    if gs is None:
        nsp = 1
        if np.any(plot_rhat):
            nsp += 1
        if np.any(plot_neff):
            nsp += 1

        gs = gridspec.GridSpec(1, nsp, width_ratios=[3] + [1] * (nsp - 1))

        if np.any(plot_rhat):
            gr_rhat = plt.subplot(gs[1])
            gr_rhat.set_xticks((1.0, 2.0))
            gr_rhat.set_xlim(0.9, 2.1)
            gr_rhat.set_yticks([])
            gr_rhat.set_title('R-hat', fontsize=textsize)
            gr_rhat.tick_params(labelsize=textsize)
        if np.any(plot_neff):
            neffs = []
            for tr in trace:
                neffs.extend(effective_n(tr).values)
            mins, maxs = round(min(neffs), -1),  round(max(neffs), -1)
            gr_neff = plt.subplot(gs[nsp-1])
            gr_neff.set_xticks((mins, maxs))
            gr_neff.set_yticks([])
            gr_neff.set_title('n_eff', fontsize=textsize)
            gr_neff.tick_params(labelsize=textsize)
    # Subplot for confidence intervals
    interval_plot = plt.subplot(gs[0])

    trace_quantiles = []
    hpd_intervals = []
    for tr in trace:
        trace_quantiles.append(tr.quantile(qlist))
        hpd_intervals.append(tr.apply(lambda x: hpd(x, alpha)))

    labels = []
    var = 0
    all_quants = []
    bands = [(0.05, 0)[i % 2] for i in range(len(varnames))]
    var_old = 0.5
    for v_idx, v in enumerate(varnames):
        for h, tr in enumerate(trace):
            if plot_rhat[h]:
                R = gelman_rubin(tr)
            if plot_neff[h]:
                n_e = effective_n(tr)
            if v not in tr.columns:
                labels.append(models[h] + ' ' + v)
                y = - var
                var += 1
            else:
                # Add spacing for each chain, if more than one
                offset = [0] + [(chain_spacing * ((i + 2) / 2)) * (-1)
                                ** i for i in range(nchains[h] - 1)]
                for j in range(nchains[h]):
                    if nchains[h] > 1:
                        var_quantiles = trace_quantiles[h][v].iloc[:, j]
                        var_hpd = hpd_intervals[h][v].iloc[j]
                    else:
                        var_quantiles = trace_quantiles[h][v]
                        var_hpd = hpd_intervals[h][v]

                    quants = var_quantiles.loc[np.unique(qlist)].values

                    # Substitute HPD interval for quantile
                    quants[0] = var_hpd[0]
                    quants[-1] = var_hpd[1]

                    # Ensure x-axis contains range of current interval
                    all_quants.extend(quants)

                    if j == 0:
                        labels.append(models[h] + ' ' + v)

                    # Y coordinate with offset
                    y = - var + offset[j]

                    interval_plot = _plot_tree(interval_plot, y, quants,
                                               quartiles, colors[h],
                                               linewidth,
                                               ms,
                                               plot_kwargs)

                # Genenerate Gelman-Rubin plot
                if plot_rhat[h] and v in tr.columns:
                    gr_rhat.plot(min(R[v], 2), -var, 'o', color=colors[h], markersize=ms)
                # Genenerate effective sample size plot
                if plot_neff[h] and v in tr.columns:
                    gr_neff.plot(n_e[v], -var, 'o', color=colors[h], markersize=ms)

                var += 1

        if len(trace) > 1:
            var_new = y - chain_spacing - 0.5
            interval_plot.axhspan(var_old, var_new, facecolor='k', alpha=bands[v_idx])
            if np.any(plot_rhat):
                gr_rhat.axhspan(var_old, var_new, facecolor='k', alpha=bands[v_idx])
            if np.any(plot_neff):
                gr_neff.axhspan(var_old, var_new, facecolor='k', alpha=bands[v_idx])

            var_old = var_new

    if ylabels is not None:
        labels = ylabels

    # Update margins
    left_margin = np.max([len(x) for x in labels]) * 0.015
    gs.update(left=left_margin, right=0.95, top=0.9, bottom=0.05)

    # Define range of y-axis for forestplot and R-hat
    interval_plot.set_ylim(- var + 0.5, 0.5)
    if np.any(plot_rhat):
        gr_rhat.set_ylim(- var + 0.5, 0.5)

    if np.any(plot_neff):
        gr_neff.set_ylim(- var + 0.5, 0.5)

    plotrange = [np.min(all_quants), np.max(all_quants)]
    datarange = plotrange[1] - plotrange[0]
    interval_plot.set_xlim(plotrange[0] - 0.05 * datarange, plotrange[1] + 0.05 * datarange)

    # Add variable labels
    interval_plot.set_yticks([- l for l in range(len(labels))])
    interval_plot.set_yticklabels(labels, fontsize=plot_kwargs.get('fontsize', textsize))

    # Add title
    if main is None:
        plot_title = "{:.0f}% Credible Intervals".format((1 - alpha) * 100)
    elif main:
        plot_title = main
    else:
        plot_title = ""

    interval_plot.set_title(plot_title, fontsize=plot_kwargs.get('fontsize', textsize))

    # Add x-axis label
    if xtitle is not None:
        interval_plot.set_xlabel(xtitle)

    # Constrain to specified range
    if xlim is not None:
        interval_plot.set_xlim(*xlim)

    # Remove ticklines on y-axes
    for ticks in interval_plot.yaxis.get_major_ticks():
        ticks.tick1On = False
        ticks.tick2On = False

    for loc, spine in interval_plot.spines.items():
        if loc in ['left', 'right']:
            spine.set_color('none')  # don't draw spine

    # Reference line
    interval_plot.axvline(vline, color='k', linestyle=':')
    interval_plot.tick_params(labelsize=textsize)

    return gs


def _plot_tree(ax, y, ntiles, show_quartiles, c, linewidth, ms, plot_kwargs):
    """Helper to plot errorbars for the forestplot.

    Parameters
    ----------
    ax: Matplotlib.Axes
    y: float
        y value to add error bar to
    ntiles: iterable
        A list or array of length 5 or 3
    show_quartiles: boolean
        Whether to plot the interquartile range
    c : string
        color
    Returns
    -------

    Matplotlib.Axes with a single error bar added

    """
    # Plot outer interval
    ax.errorbar(x=(ntiles[0], ntiles[-1]), y=(y, y), lw=linewidth, color=c, zorder=1)

    if show_quartiles:
        # Plot quartile interval
        ax.errorbar(x=(ntiles[1], ntiles[3]), y=(y, y),
                    lw=plot_kwargs.get('linewidth', linewidth * 2), color=c, zorder=1)
        # Plot median
        ax.plot(ntiles[2], y, color='w', mec=c, marker=plot_kwargs.get('marker', 'o'),
                ms=plot_kwargs.get('markersize', ms), zorder=2)

    else:
        # Plot median
        ax.plot(ntiles[1], y, color='w', mec=c, marker=plot_kwargs.get('marker', 'o'),
                ms=plot_kwargs.get('markersize', ms), zorder=2)

    return ax
