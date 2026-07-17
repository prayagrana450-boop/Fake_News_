import pandas as pd

# Fake.csv load karo
df = pd.read_csv("dataset/Fake.csv", low_memory=False)

# Sirf required columns rakho
df = df[["title", "text", "subject", "date"]]

# Wapas save karo
df.to_csv("dataset/Fake.csv", index=False, encoding="utf-8-sig")

print("Fake.csv cleaned successfully!")
print(df.shape)