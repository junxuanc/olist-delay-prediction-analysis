#%%
# drop the comment and title
import pandas as pd
df=pd.read_csv('/Users/hfg/Desktop/olist datasets/olist_order_reviews_dataset.csv')

df=df.drop(columns=['review_comment_message','review_comment_title'])
df.to_csv('/Users/hfg/Desktop/olist datasets/olist_order_reviews_dataset_clean.csv',index=False)
# %%
# plot the monthly delay
import pandas as pd
import matplotlib.pyplot as plt

df_month=pd.read_csv('/Users/hfg/Desktop/olist datasets/monthly_delay.csv')

fig, ax1 = plt.subplots(figsize=(12, 5))

line1 = ax1.plot(df_month["year_month"], df_month["monthly_total_orders"], marker="o", color="blue")[0]
ax1.set_xlabel("Year-Month")
ax1.set_ylabel("Monthly Total Orders")
ax1.tick_params(axis="y")
plt.xticks(rotation=45)

ax2 = ax1.twinx()
line2 = ax2.plot(df_month["year_month"], df_month["ratio_delay_monthly"], marker="s", color="orange")[0]
ax2.set_ylabel("Monthly Delay Ratio")
ax2.tick_params(axis="y")

ax1.legend([line1, line2], ["Order Count", "Delay Ratio"], loc="upper right")

plt.title("Monthly Order Volume and Delivery Delay Ratio")
plt.tight_layout()
plt.show()
# %%
#delivery_raw box plot
import pandas as pd
import matplotlib.pyplot as plt

df_raw = pd.read_csv("/Users/hfg/Desktop/olist datasets/delivery_raw.csv")

# change PostgreSQL's interval string into actual number of day
df_raw["delivery_days"] = pd.to_timedelta(df_raw["delivery_interval"]).dt.total_seconds() / (24 * 3600)

plt.figure(figsize=(8, 5))
df_raw.boxplot(column="delivery_days", by="is_delay", grid=False)
plt.title("Delivery Duration: On-time vs Delayed Orders")

#delete the auto-title by the program
plt.suptitle("") 
plt.xlabel("0 = On-time | 1 = Delayed")
plt.ylabel("Delivery Days")
plt.show()
# %%
#load the join table
import pandas as pd

join_table=pd.read_csv('/Users/hfg/Desktop/olist datasets/join table.csv')
print(join_table.shape)
print(join_table.info())
join_table.isna().sum()
join_table

# %%
#clean the missing value 

# filling with median
median_cols = ["total_weight","avg_length","avg_height","avg_width","avg_photos","avg_installments"]

for col in median_cols:
    join_table[col] = join_table[col].fillna(join_table[col].median())

# filling with mode
join_table["payment_type"] = join_table["payment_type"].fillna(join_table["payment_type"].mode()[0])

print(join_table.isna().sum())
# %%
# change into datetime
join_table["order_purchase_timestamp"] = pd.to_datetime(join_table["order_purchase_timestamp"])
join_table["purchase_month"] = join_table["order_purchase_timestamp"].dt.month      # 1‑12
join_table["purchase_dow"] = join_table["order_purchase_timestamp"].dt.dayofweek   # 0=周一，6=周日

# one-hot
df_onehot = pd.get_dummies(join_table["payment_type"], drop_first=True)
join_table = pd.concat([join_table, df_onehot], axis=1)
# %%
join_table
# %%
feature_cols = [
    "item_count","product_count","total_price","total_freight",
    "total_weight","avg_length","avg_height","avg_width","avg_photos",
    "avg_installments","purchase_month","purchase_dow",
    "credit_card", "debit_card", "voucher"
]

x = join_table[feature_cols].copy()
y = join_table["is_delay"].copy()
# %%
#split the train and test datasets
from sklearn.model_selection import train_test_split
x_train, x_test, y_train, y_test = train_test_split(
    x,y,
    test_size=0.2,
    random_state=42,
    stratify=y
)
#%%
#randomforest model to forcast 
import numpy as np
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score, roc_auc_score

# gridsearch for best parameters
param_grid = {
    "n_estimators": [100, 200],          # 树的数量
    "max_depth": [10, 20, None],         # 最大深度；None=不限制深度
    "min_samples_leaf": [2, 4]           # 叶子节点最少样本数
}
rf_base = RandomForestClassifier(class_weight="balanced", random_state=42, n_jobs=-1)

# 5 fold-cross validation, using ROC-AUC to judge
cv_strat = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
grid_search = GridSearchCV(
    estimator=rf_base,
    param_grid=param_grid,
    cv=cv_strat,
    scoring="roc_auc",
    n_jobs=-1
)

grid_search.fit(x_train, y_train)

# output the best parameters and best cross validation result
print("Best Hyperparameters:", grid_search.best_params_)
print("Best Cross-Validation ROC-AUC:", grid_search.best_score_.round(3))

# use the best result to do the estimation
rf_best = grid_search.best_estimator_

# find the appropriate threshold
y_pred_proba = rf_best.predict_proba(x_test)[:,1]
thresholds = np.linspace(0.1, 0.7, 100)
best_f1 = 0
best_threshold = 0
best_metrics = {}

for t in thresholds:
    y_temp = (y_pred_proba >= t).astype(int)
    f1 = f1_score(y_test, y_temp)
    precision = precision_score(y_test, y_temp)
    recall = recall_score(y_test, y_temp)
    
    if f1 > best_f1:
        best_f1 = f1
        best_threshold = t
        best_metrics = {
            "precision": precision,
            "recall": recall,
            "f1": f1
        }

print(f"Best Threshold: {best_threshold:.3f}")
print(f"Best Precision: {best_metrics['precision']:.3f}")
print(f"Best Recall: {best_metrics['recall']:.3f}")
print(f"Best F1 Score: {best_metrics['f1']:.3f}")
print(f"ROC-AUC (test set): {roc_auc_score(y_test, y_pred_proba):.3f}")
y_pred_best = (y_pred_proba >= best_threshold).astype(int)
print("\nConfusion Matrix:\n", confusion_matrix(y_test, y_pred_best))

# %%
import pandas as pd
import matplotlib.pyplot as plt

# feature_importance ranking
feature_importance = pd.DataFrame({
    "feature": x.columns,
    "importance": rf_best.feature_importances_
}).sort_values("importance", ascending=False).reset_index(drop=True)

# we extract top 10 important features
top10_feature = feature_importance.head(10)

plt.figure(figsize=(10,6))
plt.barh(top10_feature["feature"], top10_feature["importance"])
plt.gca().invert_yaxis() 
plt.xlabel("Feature Importance")
plt.title("Top 10 Feature Importance | Random Forest")
plt.tight_layout()
plt.show()

print("Top 10 Features:")
print(top10_feature)
# %%
