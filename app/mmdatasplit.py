import pandas as pd
df = pd.read_csv("F:/CustomLLM/chuncks/10m_data_part_1.csv")
df.head()  
response_id_counts = df['ResponseID'].value_counts()
multiple_rows_response_ids = response_id_counts[response_id_counts == 2].index

df_1 = df[df['ResponseID'].isin(multiple_rows_response_ids)]
df_sorted = df_1.sort_values(by='ResponseID')
df_sorted.reset_index(drop=True, inplace=True)

df1 = df_sorted[df_sorted.index % 2 == 0].reset_index(drop=True)
df2 = df_sorted[df_sorted.index % 2 != 0].reset_index(drop=True)

df1.to_csv('case1.csv', index=False)
df2.to_csv('case2.csv', index=False)