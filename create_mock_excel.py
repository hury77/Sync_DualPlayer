import pandas as pd

data = {
    "Source": ["AVAILABLE", "APRIL 30, 2026", "PRE-ORDER FOR BONUS ARMOR SET"],
    "Polish": ["PREMIERA", "30 KWIETNIA 2026", "ZAMÓW W PRZEDSPRZEDAŻY I ODBIERZ DODATKOWY ZESTAW PANCERZA"],
    "French": ["DISPONIBLE", "30 AVRIL 2026", "PRÉCOMMANDEZ POUR OBTENIR UN ENSEMBLE D'ARMURE BONUS"]
}

df = pd.DataFrame(data)

# Add some empty rows at the top to simulate real copydeck
df_empty = pd.DataFrame([["", "", ""], ["", "", ""]], columns=df.columns)
df_final = pd.concat([df_empty, df]).reset_index(drop=True)

df_final.to_excel("mock_copydeck.xlsx", index=False, header=True)
print("mock_copydeck.xlsx created.")
