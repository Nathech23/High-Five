import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv('patient_feedback_clean.csv')

print("=== MOYENNE DE RATING PAR FEEDBACK ===")
rating_stats = df.groupby('feedback_text')['rating'].agg(['mean', 'std', 'count']).round(2)
rating_stats = rating_stats.sort_values('mean')
print(rating_stats)

# Créer visualisations
plt.figure(figsize=(15, 10))

# Graphique 1: Distribution des ratings par feedback
plt.subplot(2, 2, 1)
feedback_rating_dist = df.groupby(['feedback_text', 'rating']).size().unstack(fill_value=0)
sns.heatmap(feedback_rating_dist, annot=True, fmt='d', cmap='Blues')
plt.title('Distribution des ratings par feedback')
plt.ylabel('Feedback')

# Graphique 2: Moyenne des ratings
plt.subplot(2, 2, 2)
means = rating_stats['mean'].values
feedbacks = [f.replace('.', '') for f in rating_stats.index]
colors = ['red' if 'confusion' in f or 'difficulty' in f or 'Slow' in f or 'wait' in f or 'issues' in f 
          else 'green' for f in rating_stats.index]
plt.barh(feedbacks, means, color=colors)
plt.xlabel('Moyenne rating')
plt.title('Moyenne des ratings par feedback')

# Graphique 3: Écart-type (disparité)
plt.subplot(2, 2, 3)
stds = rating_stats['std'].values
plt.barh(feedbacks, stds)
plt.xlabel('Écart-type des ratings')
plt.title('Disparité des ratings (écart-type)')

# Graphique 4: Box plot
plt.subplot(2, 2, 4)
df_plot = df.copy()
df_plot['feedback_short'] = df_plot['feedback_text'].str.replace('.', '')
sns.boxplot(data=df_plot, y='feedback_short', x='rating')
plt.title('Distribution complète des ratings')

plt.tight_layout()
#plt.savefig('rating_analysis.png', dpi=150, bbox_inches='tight')
plt.show()

#print("\n Graphique sauvegardé : rating_analysis.png")