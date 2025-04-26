import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
import tensorflow as tf # type: ignore
from keras.models import Sequential # type: ignore
from keras.layers import LSTM, Dense, Dropout # type: ignore
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib.pyplot as plt
import joblib

# Set random seed for reproducibility
np.random.seed(42)
tf.random.set_seed(42)

# 1. Load and preprocess data
print("Loading data...")
file_path = "powerdemand_5min_2021_to_2024_with_weather.csv"
df = pd.read_csv(file_path)

# Standardizing column names to avoid errors
df.columns = df.columns.str.strip()

# Drop unnecessary columns safely
df.drop(['Unnamed: 0', 'moving_avg_3'], axis=1, errors='ignore', inplace=True)

# Convert datetime column and set index
if 'datetime' in df.columns:
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
else:
    raise KeyError("The dataset must contain a 'datetime' column.")

# Ensure 'Power demand' exists before proceeding
if 'Power demand' not in df.columns:
    raise KeyError("Column 'Power demand' not found in dataset. Available columns: ", df.columns)

# 2. Feature Engineering
print("Creating features...")

# Create lag features
for i in [1, 3, 6]:
    df[f'power_lag_{i}'] = df['Power demand'].shift(i)

# Create rolling means
df['rolling_mean_3'] = df['Power demand'].rolling(window=3).mean()
df['rolling_mean_6'] = df['Power demand'].rolling(window=6).mean()

# Extract time-based features
df['hour'] = df.index.hour
df['day_of_week'] = df.index.dayofweek
df['month'] = df.index.month
df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)

# Handle missing values
df.fillna(method='ffill', inplace=True)
df.fillna(method='bfill', inplace=True)

# 3. Scale the data
print("Scaling data...")
scaler = MinMaxScaler()
scaled_data = scaler.fit_transform(df)
df_scaled = pd.DataFrame(scaled_data, columns=df.columns, index=df.index)

# Save scaler for future use
joblib.dump(scaler, 'power_demand_scaler.pkl')

# 4. Create sequences for LSTM
print("Creating sequences...")

def create_sequences(data, target_column, seq_length):
    X, y = [], []
    data_array = data.values
    target_idx = data.columns.get_loc(target_column)

    for i in range(len(data) - seq_length):
        X.append(data_array[i:(i + seq_length)])
        y.append(data_array[i + seq_length, target_idx])
    
    return np.array(X), np.array(y)

# Parameters
SEQUENCE_LENGTH = 30  # 2.5 hours of 5-minute intervals
TARGET_COLUMN = 'Power demand'

# Create sequences
X, y = create_sequences(df_scaled, TARGET_COLUMN, SEQUENCE_LENGTH)

# 5. Split the data
print("Splitting data...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, shuffle=False
)

# 6. Build and compile the LSTM model
print("Building model...")
model = Sequential([
    LSTM(64, return_sequences=True, input_shape=(SEQUENCE_LENGTH, X.shape[2])),
    Dropout(0.2),
    LSTM(32, return_sequences=False),
    Dropout(0.2),
    Dense(16, activation='relu'),
    Dense(1)
])

model.compile(optimizer='adam', loss='mse', metrics=['mae'])

# Print model summary
model.summary()

# 7. Train the model
print("Training model...")
history = model.fit(
    X_train, y_train,
    epochs=50,
    batch_size=32,
    validation_split=0.1,
    callbacks=[
        tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True),
        tf.keras.callbacks.ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=3, min_lr=0.0001)
    ],
    verbose=1
)

# 8. Save the trained model
model.save('power_demand_lstm.h5')
print("Model saved as 'power_demand_lstm.h5'")

# 9. Evaluate the model
print("\nEvaluating model...")
y_pred = model.predict(X_test)

# Calculate metrics
mae = mean_absolute_error(y_test, y_pred)
mse = mean_squared_error(y_test, y_pred)
rmse = np.sqrt(mse)
r2 = r2_score(y_test, y_pred)

print(f"Mean Absolute Error: {mae:.4f}")
print(f"Root Mean Square Error: {rmse:.4f}")
print(f"R² Score: {r2:.4f}")

# 10. Visualizations
print("\nCreating visualizations...")
plt.figure(figsize=(15, 5))

# Loss plot
plt.subplot(1, 2, 1)
plt.plot(history.history['loss'], label='Training Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.title('Model Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()

# Predictions vs Actual
plt.subplot(1, 2, 2)
plt.plot(y_test[:100], label='Actual')
plt.plot(y_pred[:100], label='Predicted')
plt.title('Actual vs Predicted Power Demand')
plt.xlabel('Time Steps')
plt.ylabel('Scaled Power Demand')
plt.legend()

plt.tight_layout()
plt.show()

# 11. Function for making future predictions
def predict_future(model, last_sequence, n_steps):
    """
    Make future predictions using the last known sequence
    """
    future_predictions = []
    current_sequence = last_sequence.copy()
    
    for _ in range(n_steps):
        # Reshape for prediction
        current_sequence_reshaped = current_sequence.reshape(1, SEQUENCE_LENGTH, -1)
        
        # Predict next step
        next_pred = model.predict(current_sequence_reshaped, verbose=0)
        
        # Store the predicted value
        future_predictions.append(next_pred[0, 0])
        
        # Shift sequence and update with new prediction
        current_sequence = np.roll(current_sequence, -1, axis=0)
        current_sequence[-1] = current_sequence[-2]  # Copy previous values for other features
        current_sequence[-1, df_scaled.columns.get_loc(TARGET_COLUMN)] = next_pred[0, 0]
    
    return np.array(future_predictions)

# Make future predictions
print("\nMaking future predictions...")
last_sequence = X_test[-1]
future_steps = 24  # Predict next 2 hours (24 * 5 minutes)
future_predictions = predict_future(model, last_sequence, future_steps)

# Plot future predictions
plt.figure(figsize=(12, 6))
plt.plot(future_predictions, label='Future Predictions')
plt.title('Power Demand Forecast (Next 2 Hours)')
plt.xlabel('Time Steps (5-min intervals)')
plt.ylabel('Scaled Power Demand')
plt.legend()
plt.tight_layout()
plt.show()

print("\nDone! Check the plots for visualization of results.")

# Optional: Save predictions to file
np.save('future_predictions.npy', future_predictions)
