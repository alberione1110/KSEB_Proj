import os
import librosa
import numpy as np
import pandas as pd

def extract_features(file_path, sr=16000, n_mfcc=13):
    y, sr = librosa.load(file_path, sr=sr)
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
    mfccs_mean = np.mean(mfccs.T, axis=0)
    return mfccs_mean

def process_audio_directory(directory_path):
    features = []
    filenames = []
  
    
    for file_name in os.listdir(directory_path):
        if file_name.endswith('.wav'):
            file_path = os.path.join(directory_path, file_name)
            try:
                mfcc_feat = extract_features(file_path)
                features.append(mfcc_feat)
                filenames.append(file_name)
            except Exception as e:
                print(f"Error processing {file_name}: {e}")
    
    df = pd.DataFrame(features)
    df['filename'] = filenames
    return df

if __name__ == "__main__":
    df = process_audio_directory('./dementia_audio/audio_samples')
    df.to_csv('audio_features.csv', index=False)
    print("Saved audio features to audio_features.csv")