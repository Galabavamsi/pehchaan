"""matplotlib -> SVG with text kept as <text> (svg.fonttype='none') so the deck's fonts apply."""
import numpy as np, matplotlib
matplotlib.use('svg')
import matplotlib.pyplot as plt
plt.rcParams.update({'svg.fonttype': 'none', 'font.family': 'Inter', 'font.size': 11, 'axes.edgecolor': '#9AA3AE',
                     'axes.spines.top': False, 'axes.spines.right': False, 'xtick.color': '#5A6270', 'ytick.color': '#5A6270'})
fpr = np.linspace(0, 1, 200)
fig, ax = plt.subplots(figsize=(3.8, 2.8))
for k, c, lab in [(14, '#E8772E', 'Ensemble  AUC 0.97'), (5, '#9AA3AE', 'Voice-only  AUC 0.88')]:
    ax.plot(fpr, 1 - (1 - fpr) ** k, color=c, lw=2.4, label=lab)
ax.plot([0, 1], [0, 1], ls=(0, (3, 3)), color='#C9C2B5', lw=1)
ax.set_xlabel('False-positive rate', color='#5A6270'); ax.set_ylabel('True-positive rate', color='#5A6270')
ax.legend(frameon=False, loc='lower right', fontsize=10)
fig.savefig('svg/mpl_roc.svg', transparent=True, bbox_inches='tight')
print('mpl ok')
