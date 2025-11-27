import json
import os

notebook_path = '/Users/Ujjwal/Documents/DE Project/f1_streaming_pipeline/notebooks/06.3_model_evaluation_unseen_data.ipynb'

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
    
    # Check if we already added it (idempotency check)
    if "RollingLapTimeMean" in "".join(source):
        print("Rolling features already present.")
    else:
        inserted = False
        for line in source:
            # Fix: Check for the print statement without \n first, or just "Feature engineering complete"
            if "Feature engineering complete" in line and not inserted:
                new_source.append("\n")
                new_source.append("# 6. Rolling Average LapTime (last 3 laps)\n")
                new_source.append("if 'Driver' in df.columns and 'LapNumber' in df.columns and 'LapTime_seconds' in df.columns:\n")
                new_source.append("    df = df.sort_values(['Driver', 'LapNumber'])\n")
                new_source.append("    df['RollingLapTimeMean'] = df.groupby('Driver')['LapTime_seconds'].transform(lambda x: x.shift(1).rolling(3).mean())\n")
                new_source.append("    df['RollingLapTimeStd'] = df.groupby('Driver')['LapTime_seconds'].transform(lambda x: x.shift(1).rolling(3).std())\n")
                new_source.append("    # Fill NaNs\n")
                new_source.append("    df['RollingLapTimeMean'] = df['RollingLapTimeMean'].fillna(df['LapTime_seconds'])\n")
                new_source.append("    df['RollingLapTimeStd'] = df['RollingLapTimeStd'].fillna(0)\n")
                new_source.append("    # Convert TrackStatus to numeric\n")
                new_source.append("    if 'TrackStatus' in df.columns:\n")
                new_source.append("        df['TrackStatus'] = pd.to_numeric(df['TrackStatus'], errors='coerce').fillna(1)\n")
                new_source.append("    print(f\"  ✅ Rolling features created\")\n")
                new_source.append("\n")
                inserted = True
            new_source.append(line)
        nb['cells'][feat_idx]['source'] = new_source
        print("Modified feature engineering cell.")

# 3. Modify Feature Selection (Add new features to list)
sel_idx = find_cell_index(nb, "pit_stop_features = [")
if sel_idx != -1:
    source = nb['cells'][sel_idx]['source']
    if "'TrackStatus'," in "".join(source):
        print("Features already added.")
    else:
        new_source = []
        for line in source:
            new_source.append(line)
            if "'IntervalToPositionAhead'," in line:
                new_source.append("    'TrackStatus',\n")
                new_source.append("    'RollingLapTimeMean',\n")
                new_source.append("    'RollingLapTimeStd',\n")
        nb['cells'][sel_idx]['source'] = new_source
        print("Modified feature selection cell.")

# 4. Modify Prediction to use Threshold
pred_idx = find_cell_index(nb, "y_pred = model.predict(X_test_scaled)")
if pred_idx == -1:
    pred_idx = find_cell_index(nb, "# Make predictions with threshold")

if pred_idx != -1:
    source = nb['cells'][pred_idx]['source']
    new_source = []
    
    # Rewrite the cell completely to ensure correct order
    # 1. Load Threshold
    new_source.append("# Load threshold\n")
    new_source.append("threshold_path = os.path.join(models_dir, \"pit_stop_threshold.json\")\n")
    new_source.append("if os.path.exists(threshold_path):\n")
    new_source.append("    with open(threshold_path, 'r') as f:\n")
    new_source.append("        threshold_data = json.load(f)\n")
    new_source.append("    threshold = threshold_data.get('threshold', 0.5)\n")
    new_source.append("    print(f\"✅ Loaded threshold: {threshold}\")\n")
    new_source.append("else:\n")
    new_source.append("    threshold = 0.5\n")
    new_source.append("    print(f\"⚠️  Threshold file not found, using default: {threshold}\")\n")
    new_source.append("\n")
    
    # 2. Scale Features (Explicitly add this)
    new_source.append("# Scale features using the trained scaler\n")
    new_source.append("print(\"Scaling features...\")\n")
    new_source.append("X_test_scaled = scaler.transform(X_test)\n")
    new_source.append("print(f\"✅ Features scaled: {X_test_scaled.shape}\")\n")
    new_source.append("\n")
    
    # 3. Make Predictions
    new_source.append("# Make predictions with threshold\n")
    new_source.append("print(\"\\nMaking predictions on unseen data...\")\n")
    new_source.append("y_pred_proba = model.predict_proba(X_test_scaled)[:, 1]\n")
    new_source.append("y_pred = (y_pred_proba >= threshold).astype(int)\n")
    new_source.append("\n")
    
    # 4. Keep the rest (printing results) - Explicitly add them instead of relying on source
    new_source.append("# Make predictions\n")
    new_source.append("\n")
    new_source.append("print(f\"✅ Predictions made:\")\n")
    new_source.append("print(f\"  Predicted class 0: {(y_pred == 0).sum():,} ({(y_pred == 0).sum()/len(y_pred)*100:.2f}%)\")\n")
    new_source.append("print(f\"  Predicted class 1: {(y_pred == 1).sum():,} ({(y_pred == 1).sum()/len(y_pred)*100:.2f}%)\")\n")
    new_source.append("\n")
    
    # We ignore the 'source' completely now to avoid duplication on re-runs
        
    nb['cells'][pred_idx]['source'] = new_source
    print("Modified prediction cell (rewritten completely).")

# 5. Add imports for json if missing
import_idx = find_cell_index(nb, "import sys")
if import_idx != -1:
    source = nb['cells'][import_idx]['source']
    if "import json" not in "".join(source):
        new_source = ["import json\n"] + source
        nb['cells'][import_idx]['source'] = new_source
        print("Added json import.")

with open(notebook_path, 'w') as f:
    json.dump(nb, f, indent=2)

print("Notebook 6.3 modification complete.")
