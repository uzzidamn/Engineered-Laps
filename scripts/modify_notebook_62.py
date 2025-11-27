import json
import os

notebook_path = '/Users/Ujjwal/Documents/DE Project/f1_streaming_pipeline/notebooks/06.2_ml_model_pit_pred.ipynb'

with open(notebook_path, 'r') as f:
    nb = json.load(f)

# Helper to find cell by content
def find_cell_index(nb, content_snippet):
    for i, cell in enumerate(nb['cells']):
        if cell['cell_type'] == 'code':
            source = ''.join(cell['source'])
            if content_snippet in source:
                return i
    return -1

# 1. Modify Aggregation (Add TrackStatus)
agg_idx = find_cell_index(nb, "agg_dict = {}")
if agg_idx != -1:
    source = nb['cells'][agg_idx]['source']
    new_source = []
    for line in source:
        new_source.append(line)
        if "agg_dict[col] = 'first'" in line:
            new_source.append("\n")
            new_source.append("    # TrackStatus: take max (to capture any SC/VSC/RedFlag during the lap)\n")
            new_source.append("    if 'TrackStatus' in df_telemetry.columns:\n")
            new_source.append("        agg_dict['TrackStatus'] = 'max'\n")
    nb['cells'][agg_idx]['source'] = new_source
    print("Modified aggregation cell.")

# 2. Modify Feature Engineering (Add Rolling Features)
feat_idx = find_cell_index(nb, "# 1. RacePercentage")
if feat_idx != -1:
    source = nb['cells'][feat_idx]['source']
    new_source = []
    for line in source:
        new_source.append(line)
        if "# 5. IntervalToPositionAhead" in line:
             # Insert before this
             pass
    
    # Actually, let's just append the new features before the print statement
    final_source = []
    inserted = False
    for line in source:
        if "print(f\"\\n✅ Feature engineering complete" in line and not inserted:
            final_source.append("\n")
            final_source.append("# 6. Rolling Average LapTime (last 3 laps)\n")
            final_source.append("if 'Driver' in df.columns and 'LapNumber' in df.columns and 'LapTime_seconds' in df.columns:\n")
            final_source.append("    df = df.sort_values(['Driver', 'LapNumber'])\n")
            final_source.append("    df['RollingLapTimeMean'] = df.groupby('Driver')['LapTime_seconds'].transform(lambda x: x.shift(1).rolling(3).mean())\n")
            final_source.append("    df['RollingLapTimeStd'] = df.groupby('Driver')['LapTime_seconds'].transform(lambda x: x.shift(1).rolling(3).std())\n")
            final_source.append("    # Fill NaNs (first few laps) with current lap time or 0\n")
            final_source.append("    df['RollingLapTimeMean'] = df['RollingLapTimeMean'].fillna(df['LapTime_seconds'])\n")
            final_source.append("    df['RollingLapTimeStd'] = df['RollingLapTimeStd'].fillna(0)\n")
            final_source.append("    # Convert TrackStatus to numeric\n")
            final_source.append("    if 'TrackStatus' in df.columns:\n")
            final_source.append("        df['TrackStatus'] = pd.to_numeric(df['TrackStatus'], errors='coerce').fillna(1)\n")
            final_source.append("    print(f\"  ✅ Rolling features created\")\n")
            final_source.append("\n")
            inserted = True
        final_source.append(line)
    nb['cells'][feat_idx]['source'] = final_source
    print("Modified feature engineering cell.")

# 3. Modify Feature Selection (Add new features to list)
sel_idx = find_cell_index(nb, "pit_stop_features = [")
if sel_idx != -1:
    source = nb['cells'][sel_idx]['source']
    new_source = []
    for line in source:
        new_source.append(line)
        if "'IntervalToPositionAhead'," in line:
            new_source.append("    'TrackStatus',\n")
            new_source.append("    'RollingLapTimeMean',\n")
            new_source.append("    'RollingLapTimeStd',\n")
    nb['cells'][sel_idx]['source'] = new_source
    print("Modified feature selection cell.")

# 4. Modify Model Training (Add Threshold Tuning)
train_idx = find_cell_index(nb, "model = RandomForestClassifier")
if train_idx != -1:
    # We will replace the training logic to include threshold tuning
    # But first let's just update the model params in place if possible, or append the tuning logic
    source = nb['cells'][train_idx]['source']
    # We'll append the threshold tuning at the end of this cell or the next evaluation cell
    # Let's modify the evaluation cell instead to do the tuning
    pass

# 4. Modify Model Training (Add Threshold Tuning)
# Try to find by original marker first, then by new marker
eval_idx = find_cell_index(nb, "y_pred_test = model.predict(X_test_scaled)")
if eval_idx == -1:
    eval_idx = find_cell_index(nb, "# Find optimal threshold for F1 score")

if eval_idx != -1:
    # We will completely rewrite this cell to be sure
    # Get original content to preserve metrics calculation if needed, 
    # but simpler to just provide the full correct content for this part
    
    # We need to keep the metrics calculation part which was at the end of the cell
    # Let's look at what we have
    source = nb['cells'][eval_idx]['source']
    
    # Construct the correct sequence
    new_source = []
    
    # 1. Threshold tuning
    new_source.append("# Find optimal threshold for F1 score\n")
    new_source.append("y_pred_proba_train = model.predict_proba(X_train_scaled)[:, 1]\n")
    new_source.append("y_pred_proba_test = model.predict_proba(X_test_scaled)[:, 1]\n")
    new_source.append("thresholds = np.arange(0.1, 0.9, 0.05)\n")
    new_source.append("best_threshold = 0.5\n")
    new_source.append("best_f1 = 0\n")
    new_source.append("for thresh in thresholds:\n")
    new_source.append("    y_pred_thresh = (y_pred_proba_train >= thresh).astype(int)\n")
    new_source.append("    f1 = f1_score(y_train, y_pred_thresh)\n")
    new_source.append("    if f1 > best_f1:\n")
    new_source.append("        best_f1 = f1\n")
    new_source.append("        best_threshold = thresh\n")
    new_source.append("print(f\"\\n✅ Optimal Threshold found: {best_threshold:.2f} (Train F1: {best_f1:.4f})\")\n")
    new_source.append("\n")
    
    # 2. Apply threshold
    new_source.append("# Apply optimal threshold\n")
    new_source.append("y_pred_test = (y_pred_proba_test >= best_threshold).astype(int)\n")
    new_source.append("\n")
    
    # 3. Metrics (Explicitly add them to ensure they exist)
    new_source.append("# Calculate metrics\n")
    new_source.append("y_pred_train = model.predict(X_train_scaled)\n")
    new_source.append("train_accuracy = accuracy_score(y_train, y_pred_train)\n")
    new_source.append("train_f1 = f1_score(y_train, y_pred_train, zero_division=0)\n")
    new_source.append("\n")
    new_source.append("test_accuracy = accuracy_score(y_test, y_pred_test)\n")
    new_source.append("test_f1 = f1_score(y_test, y_pred_test, zero_division=0)\n")
    new_source.append("test_roc_auc = roc_auc_score(y_test, y_pred_proba_test)\n")
    new_source.append("\n")
    
    # Append the rest of the cell (printing results)
    # We skip the calculation lines we just added to avoid duplicates if they exist
    def is_calculation(line):
        if "y_pred_train =" in line: return True
        if "train_accuracy =" in line: return True
        if "train_f1 =" in line: return True
        if "test_accuracy =" in line: return True
        if "test_f1 =" in line: return True
        if "test_roc_auc =" in line: return True
        if "y_pred_test =" in line: return True
        if "y_pred_proba_test =" in line: return True
        if "thresholds =" in line: return True
        if "best_threshold =" in line: return True
        if "best_f1 =" in line: return True
        if "for thresh in thresholds:" in line: return True
        if "y_pred_thresh =" in line: return True
        if "f1 = f1_score" in line: return True
        if "if f1 > best_f1:" in line: return True
        if "print(f\"\\n✅ Optimal Threshold" in line: return True
        if "# Apply optimal threshold" in line: return True
        if "# Find optimal threshold" in line: return True
        if "y_pred_proba_train =" in line: return True
        return False

    for line in source:
        if not is_calculation(line):
            new_source.append(line)
            
    nb['cells'][eval_idx]['source'] = new_source
    print("Modified evaluation cell (fixed metrics).")

# 5. Save Model with Threshold (We need to save the threshold too)
# We'll add a cell to save the threshold
save_idx = find_cell_index(nb, "joblib.dump(model,")
if save_idx == -1:
    # Append a new cell for saving
    new_cell = {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "# Save model, scaler, and threshold\n",
            "import json\n",
            "models_dir = \"../models\"\n",
            "os.makedirs(models_dir, exist_ok=True)\n",
            "\n",
            "joblib.dump(model, os.path.join(models_dir, \"pit_stop_probability_model.pkl\"))\n",
            "joblib.dump(scaler, os.path.join(models_dir, \"pit_stop_probability_scaler.pkl\"))\n",
            "\n",
            "# Save features list\n",
            "with open(os.path.join(models_dir, \"pit_stop_features.txt\"), \"w\") as f:\n",
            "    for feature in X.columns:\n",
            "        f.write(f\"{feature}\\n\")\n",
            "\n",
            "# Save threshold\n",
            "with open(os.path.join(models_dir, \"pit_stop_threshold.json\"), \"w\") as f:\n",
            "    json.dump({\"threshold\": best_threshold}, f)\n",
            "\n",
            "print(\"✅ Model, scaler, features, and threshold saved\")\n"
        ]
    }
    nb['cells'].append(new_cell)
    print("Added save cell.")

with open(notebook_path, 'w') as f:
    json.dump(nb, f, indent=2)

print("Notebook modification complete.")
