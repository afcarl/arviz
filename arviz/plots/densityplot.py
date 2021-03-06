import numpy as np
import matplotlib.pyplot as plt
from .kdeplot import fast_kde
from ..stats import hpd
from ..utils import trace_to_dataframe, expand_variable_names
from .plot_utils import _scale_text

def densityplot(trace, models=None, varnames=None, alpha=0.05, point_estimate='mean',
                colors='cycle', outline=True, hpd_markers='', shade=0., bw=4.5, figsize=None,
                textsize=None, skip_first=0, ax=None):
    """
    Generates KDE plots for continuous variables and histograms for discretes ones.
    Plots are truncated at their 100*(1-alpha)% credible intervals. Plots are grouped per variable
    and colors assigned to models.

    Parameters
    ----------
    trace : Pandas DataFrame or PyMC3 trace or list of these objects
        Posterior samples
    models : list
        List with names for the models in the list of traces. Useful when
        plotting more that one trace. 
    varnames: list
        List of variables to plot (defaults to None, which results in all
        variables plotted).
    alpha : float
        Alpha value for (1-alpha)*100% credible intervals (defaults to 0.05).
    point_estimate : str or None
        Plot point estimate per variable. Values should be 'mean', 'median' or None.
        Defaults to 'mean'.
    colors : list or string, optional
        List with valid matplotlib colors, one color per model. Alternative a string can be passed.
        If the string is `cycle`, it will automatically choose a color per model from matplolib's
        cycle. If a single color is passed, e.g. 'k', 'C2' or 'red' this color will be used for all
        models. Defaults to `cycle`.
    outline : boolean
        Use a line to draw KDEs and histograms. Default to True
    hpd_markers : str
        A valid `matplotlib.markers` like 'v', used to indicate the limits of the hpd interval.
        Defaults to empty string (no marker).
    shade : float
        Alpha blending value for the shaded area under the curve, between 0 (no shade) and 1
        (opaque). Defaults to 0.
    bw : float
        Bandwidth scaling factor for the KDE. Should be larger than 0. The higher this number the
        smoother the KDE will be. Defaults to 4.5 which is essentially the same as the Scott's rule
        of thumb (the default rule used by SciPy).
    figsize : tuple
        Figure size. If None, size is (6, number of variables * 2)
    textsize: int
        Text size for labels and legend. If None it will be autoscaled based on figsize.
    skip_first : int
        Number of first samples not shown in plots (burn-in).
    ax : axes
        Matplotlib axes.

    Returns
    -------

    ax : Matplotlib axes

    """
    if not isinstance(trace, (list, tuple)):
        trace = [trace_to_dataframe(trace[skip_first:], combined=True)]
    else:
        trace = [trace_to_dataframe(tr[skip_first:], combined=True) for tr in trace]

    if point_estimate not in ('mean', 'median', None):
        raise ValueError("Point estimate should be 'mean', 'median' or None")

    length_trace = len(trace)

    if models is None:
        if length_trace > 1:
            models = ['m_{}'.format(i) for i in range(length_trace)]
        else:
            models = ['']
    elif len(models) != length_trace:
        raise ValueError(
            "The number of names for the models does not match the number of models")

    length_models = len(models)

    if colors == 'cycle':
        colors = ['C{}'.format(i % 10) for i in range(length_models)]
    elif isinstance(colors, str):
        colors = [colors for i in range(length_models)]

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

    if figsize is None:
        figsize = (6, len(varnames) * 2)

    textsize, lw, ms = _scale_text(figsize, textsize=textsize)

    fig, dplot = plt.subplots(len(varnames), 1, squeeze=False, figsize=figsize)
    dplot = dplot.flatten()

    for v_idx, vname in enumerate(varnames):
        for t_idx, tr in enumerate(trace):
            if vname in tr.columns:
                vec = tr[vname].values
                _d_helper(vec, vname, colors[t_idx], bw, textsize, lw, ms, alpha, point_estimate,
                          hpd_markers, outline, shade, dplot[v_idx])

    if length_trace > 1:
        for m_idx, m in enumerate(models):
            dplot[0].plot([], label=m, c=colors[m_idx], markersize=ms)
        dplot[0].legend(fontsize=textsize)

    fig.tight_layout()

    return dplot


def _d_helper(vec, vname, c, bw, textsize, lw, ms, alpha, point_estimate, hpd_markers, outline,
              shade, ax):
    """
    vec : array
        1D array from trace
    vname : str
        variable name
    c : str
        matplotlib color
    bw : float
        Bandwidth scaling factor. Should be larger than 0. The higher this number the smoother the
        KDE will be. Defaults to 4.5 which is essentially the same as the Scott's rule of thumb
        (the default used rule by SciPy).
    alpha : float
        Alpha value for (1-alpha)*100% credible intervals (defaults to 0.05).
    point_estimate : str or None
        'mean' or 'median'
    shade : float
        Alpha blending value for the shaded area under the curve, between 0 (no shade) and 1
        (opaque). Defaults to 0.
    ax : matplotlib axes
    """
    if vec.dtype.kind == 'f':
        density, l, u = fast_kde(vec)
        x = np.linspace(l, u, len(density))
        hpd_ = hpd(vec, alpha)
        cut = (x >= hpd_[0]) & (x <= hpd_[1])

        xmin = x[cut][0]
        xmax = x[cut][-1]
        ymin = density[cut][0]
        ymax = density[cut][-1]

        if outline:
            ax.plot(x[cut], density[cut], color=c, lw=lw)
            ax.plot([xmin, xmin], [-ymin/100, ymin], color=c, ls='-', lw=lw)
            ax.plot([xmax, xmax], [-ymax/100, ymax], color=c, ls='-', lw=lw)

        if shade:
            ax.fill_between(x, density, where=cut, color=c, alpha=shade)

    else:
        xmin, xmax = hpd(vec, alpha)
        bins = range(xmin, xmax + 2)
        if outline:
            ax.hist(vec, bins=bins, color=c, histtype='step', align='left')
        if shade:
            ax.hist(vec, bins=bins, color=c, alpha=shade)

    if hpd_markers:
        ax.plot(xmin, 0, 'v', color=c, markeredgecolor='k', markersize=ms)
        ax.plot(xmax, 0, 'v', color=c, markeredgecolor='k', markersize=ms)

    if point_estimate is not None:
        if point_estimate == 'mean':
            ps = np.mean(vec)
        elif point_estimate == 'median':
            ps = np.median(vec)
        ax.plot(ps, -0.001, 'o', color=c, markeredgecolor='k', markersize=ms)

    ax.set_yticks([])
    ax.set_title(vname)
    for pos in ['left', 'right', 'top']:
        ax.spines[pos].set_visible(0)
    ax.tick_params(labelsize=textsize)
