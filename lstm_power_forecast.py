import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib.pyplot as plt
import joblib

# Load data from Excel file
file_path = r"C:\Users\Sakshi Shah\Downloads\archive\powerdemand_5min_2021_to_2024_with weather.csv"
df = pd.read_csv(file_path)

# Drop unnecessary columns if they exist
columns_to_drop = ["Unnamed: 0", "moving_avg_3"]
df = df.drop(columns=[col for col in columns_to_drop if col in df.columns], errors="ignore")

# Convert datetime column to proper format
df["datetime"] = pd.to_datetime(df["datetime"], errors='coerce')

# Set datetime as index
df.set_index("datetime", inplace=True)

# Handle missing values (forward fill)
df.fillna(method='ffill', inplace=True)

# Create lag features (previous demand values)
df['lag_1'] = df['Power demand'].shift(1)
df['lag_3'] = df['Power demand'].shift(3)
df['lag_6'] = df['Power demand'].shift(6)

# Create rolling average features
df['rolling_mean_3'] = df['Power demand'].rolling(window=3).mean()
df['rolling_mean_6'] = df['Power demand'].rolling(window=6).mean()

# Extract time-based features
df['day_of_week'] = df.index.dayofweek  # Monday = 0, Sunday = 6
df['hour'] = df.index.hour  # Extract hour of the day
df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)  # 1 for weekend, 0 for weekdays

# Handle missing values created by shifting
df.fillna(method='bfill', inplace=True)

# Data scaling
numeric_features = df.select_dtypes(include=[np.number]).columns
scaler = MinMaxScaler()
df_scaled = pd.DataFrame(scaler.fit_transform(df[numeric_features]), 
                        columns=numeric_features, 
                        index=df.index)

# Save the scaler for later use
joblib.dump(scaler, "scaler.pkl")

# Define time steps for LSTM
TIME_STEPS = 30  # Looking back 30 timesteps (~2.5 hours for 5-min data)

# Function to create sequences for LSTM
def create_sequences(data, time_steps):
    X, Y = [], []
    for i in range(len(data) - time_steps):
        X.append(data.iloc[i : i + time_steps].values)
        Y.append(data.iloc[i + time_steps]["Power demand"])
    return np.array(X), np.array(Y)

# Create sequences
X, Y = create_sequences(df_scaled, TIME_STEPS)

# Split into train (80%) and test (20%) sets
X_train, X_test, Y_train, Y_test = train_test_split(X, Y, test_size=0.2, shuffle=False)

# Build LSTM model
model = Sequential([
    LSTM(50, return_sequences=True, input_shape=(X_train.shape[1], X_train.shape[2])),
    Dropout(0.2),
    LSTM(50, return_sequences=False),
    Dropout(0.2),
    Dense(25, activation="relu"),
    Dense(1)  # Output layer (single value prediction)
])

# Compile the model
model.compile(optimizer='adam', loss='mse')

# Train the LSTM model
history = model.fit(
    X_train, Y_train,
    batch_size=32,
    epochs=50,
    validation_data=(X_test, Y_test),
    callbacks=[
        tf.keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=5,
            restore_best_weights=True
        )
    ],
    verbose=1
)

# Save the trained model
model.save('lstm_model.h5')

# Evaluate the model
test_loss = model.evaluate(X_test, Y_test)
print(f"Test Loss: {test_loss}")

# Make predictions
predictions = model.predict(X_test)

# Calculate metrics
mae = mean_absolute_error(Y_test, predictions)
mse = mean_squared_error(Y_test, predictions)
rmse = np.sqrt(mse)
r2 = r2_score(Y_test, predictions)

print(f"MAE: {mae}")
print(f"RMSE: {rmse}")
print(f"R2 Score: {r2}")

# Plot training history
plt.figure(figsize=(12, 4))

# Plot loss
plt.subplot(1, 2, 1)
plt.plot(history.history['loss'], label='Training Loss')
plt.plot(history.history['val_loss'], label='Validation Loss')
plt.title('Model Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()

# Plot actual vs predicted
plt.subplot(1, 2, 2)
plt.plot(Y_test[:100], label='Actual')
plt.plot(predictions[:100], label='Predicted')
plt.title('Actual vs Predicted Values')
plt.xlabel('Time Steps')
plt.ylabel('Power Demand')
plt.legend()

plt.tight_layout()
plt.show()

# Function to make future predictions
def predict_future(model, last_sequence, scaler, steps_ahead=1):
    predictions = []
    current_sequence = last_sequence.copy()
    
    for _ in range(steps_ahead):
        # Reshape the sequence correctly to match the model's input shape
        sequence_reshaped = current_sequence.reshape(1, TIME_STEPS, -1)
        next_pred = model.predict(sequence_reshaped, verbose=0)
        predictions.append(next_pred[0, 0])
        
        # Update the sequence by rolling and updating the last value
        current_sequence = np.roll(current_sequence, -1, axis=0)
        # Update all features for the new timestep (using the predicted value)
        current_sequence[-1, df_scaled.columns.get_loc('Power demand')] = next_pred[0, 0]
    
    return np.array(predictions)

# Make future predictions
last_sequence = X_test[-1]  # Get the last sequence from test data
future_predictions = predict_future(model, last_sequence, scaler, steps_ahead=24)

# Plot future predictions
plt.figure(figsize=(12, 6))
plt.plot(future_predictions, label='Future Predictions')
plt.title('Future Power Demand Predictions')
plt.xlabel('Time Steps (5-min intervals)')
plt.ylabel('Power Demand')
plt.legend()
plt.show() 